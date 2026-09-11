// Hand-written to mirror the backend's Pydantic response/request schemas
// (Decision #50) — no OpenAPI codegen in this pass, so these need to be
// kept in sync by hand if a backend schema changes.

export interface UserResponse {
  id: string;
  email: string;
  first_name: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// "twitter" retired (Decision #63) — manually-entered resources, including
// pasted tweet/thread links, use "manual" instead.
export type Source = "manual" | "chrome" | "firefox";

export interface ItemResponse {
  id: string;
  owner_user_id: string;
  source: Source;
  external_id: string;
  title: string;
  url: string;
  folder_path: string | null;
  preview_text: string | null;
  preview_media_url: string | null;
  favicon_url: string | null;
  notes: string | null;
  tags: string[];
  saved_at: string;
  created_at: string;
}

export interface BoardResponse {
  id: string;
  owner_user_id: string;
  owner_email: string | null;
  owner_first_name: string | null;
  name: string;
  created_at: string;
}

export type BoardRole = "owner" | "viewer" | "editor";

export interface BoardItemResponse {
  item_id: string;
  title: string;
  url: string;
  favicon_url: string | null;
  preview_text: string | null;
  preview_media_url: string | null;
  added_at: string;
}

export interface BoardWithItemsResponse {
  id: string;
  owner_user_id: string;
  owner_email: string | null;
  owner_first_name: string | null;
  name: string;
  created_at: string;
  role: BoardRole;
  items: BoardItemResponse[];
}

export interface InviteResponse {
  board_id: string;
  invited_email: string;
  role: BoardRole;
  invite_token: string;
  expires_at: string;
}

export interface AccessGrantSummary {
  invited_email: string;
  status: "pending" | "accepted";
  role: BoardRole;
  created_at: string;
  accepted_at: string | null;
}

export interface OwnedBoardResponse {
  id: string;
  name: string;
  created_at: string;
  item_count: number;
  grants: AccessGrantSummary[];
}

export interface SharedBoardResponse {
  id: string;
  name: string;
  owner_user_id: string;
  owner_email: string | null;
  owner_first_name: string | null;
  role: BoardRole;
  accepted_at: string;
  item_count: number;
}
