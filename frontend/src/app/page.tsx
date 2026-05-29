import { redirect } from "next/navigation";
import { getServerAuthState } from "../utils/serverAuth";

export default async function RootPage() {
  const { isAuthenticated, userRole } = await getServerAuthState();
  
  if (!isAuthenticated) {
    redirect("/login");
  }
  
  // Route admin-level users to dashboard
  if (userRole === "super_admin" || userRole === "admin" || userRole === "security_admin") {
    redirect("/admin");
  }
  
  redirect("/chat");
}
