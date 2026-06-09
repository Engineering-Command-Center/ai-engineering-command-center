export interface User {
  email: string;
  name: string;
  picture: string | null;
  is_admin?: boolean;
}
