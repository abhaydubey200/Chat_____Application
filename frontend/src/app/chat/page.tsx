import { redirect } from "next/navigation";
import { getServerAuthState } from "../../utils/serverAuth";
import ChatDashboardClient from "./ChatDashboardClient";

export default async function ChatDashboardPage() {
  const { isAuthenticated, userRole } = await getServerAuthState();

  if (!isAuthenticated) {
    redirect("/login");
  }

  // Redirect admin-level users to the admin dashboard
  if (userRole === "super_admin" || userRole === "admin" || userRole === "security_admin") {
    redirect("/admin");
  }

  return <ChatDashboardClient />;
}
