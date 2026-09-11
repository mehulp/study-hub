import { apiRequest } from "./client";
import type {
  BoardResponse,
  BoardItemResponse,
  BoardWithItemsResponse,
  InviteResponse,
  OwnedBoardResponse,
  SharedBoardResponse,
} from "../types/api";

export async function createBoard(name: string): Promise<BoardResponse> {
  return apiRequest<BoardResponse>("/board", {
    method: "POST",
    body: { name },
  });
}

export async function getBoard(boardId: string): Promise<BoardWithItemsResponse> {
  return apiRequest<BoardWithItemsResponse>(`/board/${boardId}`);
}

// Board's own route is /invites/{token}/accept (not board-id-scoped — the
// token alone identifies the grant), mounted under Gateway's "/board"
// prefix, so the full path is /board/invites/{token}/accept.
export async function acceptInvite(token: string): Promise<BoardWithItemsResponse> {
  return apiRequest<BoardWithItemsResponse>(`/board/invites/${token}/accept`, {
    method: "POST",
  });
}

export async function addItemToBoard(boardId: string, itemId: string): Promise<BoardItemResponse> {
  return apiRequest<BoardItemResponse>(`/board/${boardId}/items`, {
    method: "POST",
    body: { item_id: itemId },
  });
}

export async function removeItemFromBoard(boardId: string, itemId: string): Promise<void> {
  await apiRequest<void>(`/board/${boardId}/items/${itemId}`, { method: "DELETE" });
}

export async function createInvite(boardId: string, invitedEmail: string): Promise<InviteResponse> {
  return apiRequest<InviteResponse>(`/board/${boardId}/invite`, {
    method: "POST",
    body: { invited_email: invitedEmail },
  });
}

export async function listMyBoards(): Promise<OwnedBoardResponse[]> {
  return apiRequest<OwnedBoardResponse[]>("/board/mine");
}

export async function listSharedWithMe(): Promise<SharedBoardResponse[]> {
  return apiRequest<SharedBoardResponse[]>("/board/shared-with-me");
}
