import { apiRequest } from "./client";

interface TwitterAuthorizeResponse {
  authorize_url: string;
}

export async function getTwitterAuthorizeUrl(): Promise<string> {
  const { authorize_url } = await apiRequest<TwitterAuthorizeResponse>(
    "/connectors/twitter/authorize"
  );
  return authorize_url;
}
