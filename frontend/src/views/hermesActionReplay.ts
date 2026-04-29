export function createActionReplayGuard() {
  let initialized = false
  let lastSeen = ''

  return {
    markInitial(fingerprint: string) {
      initialized = true
      lastSeen = fingerprint
    },
    shouldProcess(fingerprint: string) {
      if (!fingerprint || !initialized) return false
      if (fingerprint === lastSeen) return false
      lastSeen = fingerprint
      return true
    },
  }
}
