export interface User {
  id: string;
  email: string;
  role: string;
  isAdmin?: boolean;
}

export interface AuthSession {
  user: User;
  accessToken: string;
}
