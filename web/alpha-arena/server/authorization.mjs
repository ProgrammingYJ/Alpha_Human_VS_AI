/** Call only with the Sites dispatch-owned identity header, never a body/query ID. */
export function ownerMatches(configuredOwner, authenticatedUserId) {
  return typeof configuredOwner === "string" && configuredOwner.length > 0
    && typeof authenticatedUserId === "string" && authenticatedUserId === configuredOwner;
}
