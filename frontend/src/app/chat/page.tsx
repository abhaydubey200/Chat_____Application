import { redirect } from "next/navigation";
import { getServerAuthState } from "../../utils/serverAuth";
import ChatDashboardClient from "./ChatDashboardClient";

export default async function ChatDashboardPage() {
  const { isAuthenticated } = await getServerAuthState();

  if (!isAuthenticated) {
    redirect("/login");
  }

  return <ChatDashboardClient />;
}
