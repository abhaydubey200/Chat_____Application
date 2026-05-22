import { redirect } from "next/navigation";
import { getServerAuthState } from "../../utils/serverAuth";
import LoginPageClient from "./LoginPageClient";

export default async function LoginPage() {
  const { isAuthenticated } = await getServerAuthState();

  if (isAuthenticated) {
    redirect("/chat");
  }

  return <LoginPageClient />;
}
