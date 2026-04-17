export type CreateProjectPayload = {
  name: string
  genre: string
}

export type CreateProjectHandler = (
  payload: CreateProjectPayload,
) => boolean | Promise<boolean>

export async function normalizeCreateProjectResult(
  createProject: CreateProjectHandler,
  payload: CreateProjectPayload,
): Promise<boolean> {
  try {
    return await createProject(payload)
  } catch {
    return false
  }
}
