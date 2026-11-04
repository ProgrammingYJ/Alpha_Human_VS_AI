"""Bounded offline stream comparison. Never changes the production scheduler."""
from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import threading
import time

from PIL import Image
import torch

from alpha_captcha.inference import TorchTilePredictor
from alpha_captcha.tree_model import TreeCountPredictor
from alpha_captcha.presence_model import preprocess_image, LABELS, predict_presence
from alpha_captcha.person_model import letterbox_person, decode_person_output, predict_person

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=Path(__file__).with_name('report.json')

def operator_count():
    command="@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like '*Alpha-Captcha-AI*run_remote_engine.py*' }).Count"
    return int(subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True).strip())

def raw_gpu():
    return subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,memory.used,utilization.gpu','--format=csv,noheader'],text=True).strip()

def canonical(value):
    if isinstance(value,dict):return {k:canonical(v) for k,v in value.items()}
    if isinstance(value,list):return [canonical(v) for v in value]
    return value

def difference(left,right):
    if isinstance(left,dict):
        return max((difference(left[k],right[k]) for k in left),default=0.0) if left.keys()==right.keys() else float('inf')
    if isinstance(left,list):
        return max((difference(a,b) for a,b in zip(left,right)),default=0.0) if len(left)==len(right) else float('inf')
    if isinstance(left,(float,int)) and isinstance(right,(float,int)):return abs(left-right)
    return 0.0 if left==right else float('inf')

def main():
    if OUTPUT.exists():raise RuntimeError('preserve_existing_report')
    count=operator_count()
    if count:raise RuntimeError('operator_engine_active_no_probe_performed')
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'operator_engine_process_count_before':count,
            'gpu_before':raw_gpu(),'device':torch.cuda.get_device_name(0),'total_memory_bytes':torch.cuda.get_device_properties(0).total_memory,
            'torch_version':torch.__version__,'torch_threads':torch.get_num_threads(),'training_performed':False,
            'production_scheduler_changed':False,'live_rooms_accessed':False,'private_labels_or_answers_read':False,
            'hardware_partition_or_50_percent_guarantee':False,'cases':[]}
    model_start=time.perf_counter()
    predictor=TorchTilePredictor.from_checkpoints(ROOT/'models/checkpoints/presence-limited-v1/presence.pt',ROOT/'models/checkpoints/person-limited-v1/person.pt',device='cuda')
    tree=TreeCountPredictor(ROOT/'models/pretrained/grounding-dino-tiny',device='cuda')
    report['model_load_seconds']=time.perf_counter()-model_start
    paths=sorted(p for p in (ROOT/'data/booth/public-web-v1/images').iterdir() if p.suffix.lower() in {'.jpg','.jpeg','.webp','.png'})[:9]
    report['image_sha256']=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    images=[]
    for path in paths:
        with Image.open(path) as image:images.append(image.convert('RGB').copy())
    lane_images=[[im.copy() for im in images] for _ in range(2)]
    trees=[]
    for _ in range(2):
        item=copy.copy(tree);item.processor=copy.deepcopy(tree.processor);item.last_detections=[];trees.append(item)
    report['safety_adaptations']=['Shared weights remain eval; no model.to/eval mutators in concurrent presence/person wrappers.',
        'Separate tree processors/tokenizers, last_detections and PIL images per lane; shared frozen tree model.',
        'Only isolated experiment wrappers are adapted; production SharedModels FIFO remains unchanged.']
    predictor.presence_model.eval();predictor.person_model.eval();tree.model.eval()
    def call(kind,lane):
        ims=lane_images[lane]
        if kind=='presence':
            rows=[]
            for offset in range(0,9,8):
                x=torch.stack([preprocess_image(im) for im in ims[offset:offset+8]]).to('cuda')
                y=predictor.presence_model(x)
                if not torch.isfinite(y).all():raise RuntimeError('nonfinite_presence')
                rows.extend(dict(zip(LABELS,row)) for row in y.sigmoid().cpu().tolist())
            return rows
        if kind=='person':
            tensors,geometries=[],[]
            for im in ims:
                x,_,g=letterbox_person(im,size=predictor.person_profile.input_size)
                tensors.append(x.to('cuda'));geometries.append(g)
            outputs=predictor.person_model(tensors)
            return [decode_person_output(row,g,predictor.person_profile) for row,g in zip(outputs,geometries)]
        return trees[lane].predict_counts(ims)
    synthetic=[Image.new('RGB',(192,192),(127,127,127)) for _ in range(9)]
    with torch.inference_mode():
        predict_presence(predictor.presence_model,synthetic,device='cuda')
        predict_person(predictor.person_model,synthetic,predictor.person_profile,device='cuda')
        tree.predict_counts(synthetic)
        # Same pixels, fixed functions; compare experimental read-only wrappers
        # with the production functions before timing any concurrent work.
        prod={'presence':predict_presence(predictor.presence_model,images,device='cuda'),
              'person':predict_person(predictor.person_model,images,predictor.person_profile,device='cuda'),
              'tree':tree.predict_counts(images)}
        baseline={k:call(k,0) for k in prod}
    report['production_output_maximum_difference']={k:difference(v,baseline[k]) for k,v in prod.items()}
    if any(v>1e-6 for v in report['production_output_maximum_difference'].values()):raise RuntimeError('wrapper_output_changed')
    ready_event=torch.cuda.Event();ready_event.record(torch.cuda.current_stream());ready_event.synchronize()
    streams=[torch.cuda.Stream(),torch.cuda.Stream()]
    for stream in streams:stream.wait_event(ready_event)
    def worker(kind,lane,gate=None,origin=None,streamed=False):
        if gate:gate.wait(timeout=30)
        started=time.perf_counter()
        stream=streams[lane] if streamed else torch.cuda.current_stream()
        with torch.inference_mode(),torch.cuda.stream(stream):
            result=call(kind,lane)
            done=torch.cuda.Event();done.record(stream)
        done.synchronize()
        ended=time.perf_counter()
        return {'kind':kind,'lane':lane,'started_seconds':started-origin,'finished_seconds':ended-origin,
                'wall_seconds':ended-started,'maximum_difference_from_serial':difference(result,baseline[kind]),'output':result}
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            for pair in [('presence','person'),('tree','presence'),('tree','tree')]:
                print('CASE '+ '+'.join(pair),flush=True)
                case={'tasks':list(pair),'repetitions':3,'serial':[],'concurrent_streams':[]}
                for mode in ['serial','concurrent_streams']:
                    # One warm invocation for this stream/mode; it is not a
                    # measured repeat or a label/model selection experiment.
                    origin=time.perf_counter()
                    if mode=='serial':
                        worker(pair[0],0,origin=origin);worker(pair[1],1,origin=origin)
                    else:
                        gate=threading.Barrier(3)
                        tasks=[pool.submit(worker,kind,lane,gate,origin,True) for lane,kind in enumerate(pair)]
                        gate.wait(timeout=30);[f.result() for f in tasks]
                    for repeat in range(3):
                        torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats()
                        origin=time.perf_counter()
                        if mode=='serial':
                            rows=[worker(pair[0],0,origin=origin),worker(pair[1],1,origin=origin)]
                        else:
                            gate=threading.Barrier(3)
                            tasks=[pool.submit(worker,kind,lane,gate,origin,True) for lane,kind in enumerate(pair)]
                            gate.wait(timeout=30);rows=[f.result() for f in tasks]
                        torch.cuda.synchronize();elapsed=time.perf_counter()-origin
                        same=all(row['maximum_difference_from_serial']<=1e-6 for row in rows)
                        for row in rows:row.pop('output')
                        case[mode].append({'repeat':repeat+1,'wall_seconds':elapsed,'lanes':rows,'same_outputs':same,
                            'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'peak_reserved_bytes':torch.cuda.max_memory_reserved(),
                            'host_call_intervals_overlap':min(r['finished_seconds'] for r in rows)>max(r['started_seconds'] for r in rows)})
                        if not same:raise RuntimeError('concurrent_output_changed')
                case['serial_median_wall_seconds']=statistics.median(v['wall_seconds'] for v in case['serial'])
                case['concurrent_median_wall_seconds']=statistics.median(v['wall_seconds'] for v in case['concurrent_streams'])
                case['median_wall_speedup']=case['serial_median_wall_seconds']/case['concurrent_median_wall_seconds']
                report['cases'].append(case)
        report['passed']=True
    except torch.cuda.OutOfMemoryError:
        report['passed']=False;report['error']='cuda_out_of_memory_no_retry'
    except Exception as error:
        report['passed']=False;report['error_type']=type(error).__name__;report['error']=str(error)[:120]
    finally:
        report['gpu_after']=raw_gpu()
        report['limitations']=['Offline saved RGB only: no HTTP, readiness barrier, competition countdown, UI or mouse control.',
            'Host invocation overlap is measured; actual simultaneous kernel execution is NOT verified without a GPU timeline.',
            'Three repeats on one fixed nine-image set are not p95, long-run stability, all image-shape coverage or accuracy.',
            'Separate CUDA streams share one GPU and its compute/memory bandwidth; no hard 50/50 partition or latency guarantee.']
        OUTPUT.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        for im in images+synthetic+sum(lane_images,[]):im.close()
    print(json.dumps({'passed':report['passed'],'cases':[{'tasks':v['tasks'],'serial_median':v['serial_median_wall_seconds'],'concurrent_median':v['concurrent_median_wall_seconds'],'speedup':v['median_wall_speedup']} for v in report['cases']]}),flush=True)
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
