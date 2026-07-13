export interface LoginCredentials {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
}

export interface UploadResponse {
  filename: string;
  size: number;
  content_type: string;
  message: string;
}
