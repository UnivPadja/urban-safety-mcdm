"use client";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "./Sidebar";
import Header from "./Header";

function PendataanAccessGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [accessChecked, setAccessChecked] = useState(false);

  useEffect(() => {
    const match = document.cookie
      .split("; ")
      .find((row) => row.startsWith("auth_session="));

    if (!match) {
      router.replace("/login");
      return;
    }

    try {
      const session = JSON.parse(
        decodeURIComponent(match.slice("auth_session=".length))
      );
      if (!session.user) {
        router.replace("/login");
        return;
      }
      if (session.user.role === "PENILAI") {
        router.replace("/");
        return;
      }
    } catch {
      router.replace("/login");
      return;
    }

    setAccessChecked(true);
  }, [router]);

  if (!accessChecked) {
    return (
      <main
        className="w-full h-screen flex items-center justify-center bg-[#F7F8F5] text-sm text-zinc-500"
        aria-live="polite"
      >
        Memeriksa akses...
      </main>
    );
  }

  return children;
}

export default function LayoutShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isLoginPage = pathname === "/login";
  if (isLoginPage) {
    return <main className="w-full min-h-screen bg-[#F7F8F5]">{children}</main>;
  }

  const page = (
    <>
      <Sidebar />
      <div className="flex-1 h-screen flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto bg-[#F7F8F5]">{children}</main>
      </div>
    </>
  );

  return pathname === "/pendataan" ? (
    <PendataanAccessGuard>{page}</PendataanAccessGuard>
  ) : (
    page
  );
}