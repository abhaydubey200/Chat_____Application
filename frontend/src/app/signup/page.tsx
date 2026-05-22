import { redirect } from "next/navigation";
import { getServerAuthState } from "../../utils/serverAuth";
import SignupPageClient from "./SignupPageClient";

export default async function SignupPage() {
  const { isAuthenticated } = await getServerAuthState();

  if (isAuthenticated) {
    redirect("/chat");
  }

  return <SignupPageClient />;
}
