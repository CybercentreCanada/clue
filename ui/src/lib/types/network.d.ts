/**
 * The specification interface of an Clue HTTP response.
 */
export type ClueResponse<R> = {
  api_response: R;
  api_error_message: string;
  api_server_version: string;
  api_status_code: number;
};
