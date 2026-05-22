import { redirect } from "next/navigation";
import { getServerAuthState } from "../utils/serverAuth";

export default async function RootPage() {
  const { isAuthenticated } = await getServerAuthState();
  redirect(isAuthenticated ? "/chat" : "/login");
}
