"use client";

import { use, useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppUserAccount, fetchUsers, updateUserRole } from "../../../lib/api";
import { UserRole } from "../../../lib/auth";

export default function EditHakAksesPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();

  const [user, setUser] = useState<AppUserAccount | null>(null);
  const [selectedRole, setSelectedRole] = useState<UserRole>("PJU");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    async function loadUser() {
      try {
        const users = await fetchUsers();
        const numId = parseInt(id, 10);
        const found = users.find(
          (u) => u.id === numId || String(u.id) === id || u.username === id
        );
        if (found) {
          setUser(found);
          setSelectedRole(found.role);
        }
      } catch {
      } finally {
        setLoading(false);
      }
    }
    loadUser();
  }, [id]);

  const permissions = [
    { label: "Kelola segmen dan inspeksi", allowed: selectedRole === "PJU" || selectedRole === "ADMIN",},
    { label: "Nilai dan aktifkan bobot AHP", allowed: selectedRole === "PENILAI" || selectedRole === "ADMIN",},
    { label: "Tetapkan daftar kerja PJU", allowed: selectedRole === "PJU" || selectedRole === "ADMIN",},
    { label: "Kelola akun dan izin", allowed: selectedRole === "ADMIN",},
  ];

  async function handleSave() {
    if (!user) return;
    setSaving(true);
    try {
      await updateUserRole(user.id, selectedRole);
      setSaveSuccess(true);
      setTimeout(() => {
        router.push("/akun-akses");
      }, 700);
    } catch {
      alert("Gagal memperbarui hak akses pengguna.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="p-8 bg-[#F7F8F5] min-h-full">
        <p className="text-xs text-zinc-500">Memuat data pengguna...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="p-8 bg-[#F7F8F5] min-h-full">
        <div className="bg-white rounded-2xl border border-zinc-200/80 p-8 shadow-xs max-w-xl">
          <h1 className="text-lg font-bold text-zinc-900 mb-2">Pengguna tidak ditemukan</h1>
          <p className="text-xs text-zinc-500 mb-5">Akun pengguna dengan pengenal &ldquo;{id}&rdquo; tidak terdaftar di sistem.</p>
          <Link href="/akun-akses" className="px-4 py-2 rounded-lg border border-zinc-200 text-zinc-700 hover:bg-zinc-50 text-xs font-medium transition">&larr; Kembali ke akun dan akses</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 bg-[#F7F8F5] min-h-full">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900 leading-tight">Edit hak akses</h1>
        <p className="text-xs text-zinc-500 mt-1">Atur peran dan izin akun pengguna.</p>
      </div>

      <div className="bg-white rounded-2xl border border-zinc-200/80 p-8 shadow-xs max-w-2xl">
        <div className="mb-5">
          <h2 className="text-base font-bold text-zinc-900">{user.full_name}</h2>
          <p className="text-xs text-zinc-400 mt-0.5">{user.email}</p>
        </div>

        <div className="mb-6">
          <label className="block text-xs font-medium text-zinc-700 mb-1.5">Peran</label>
          <div className="relative">
            <select value={selectedRole} onChange={(e) => setSelectedRole(e.target.value as UserRole)} className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-200 text-sm text-zinc-800 bg-white font-normal shadow-2xs appearance-none pr-10 focus:outline-none focus:ring-1 focus:ring-[#1a5b3e] cursor-pointer">
              <option value="PENILAI">Penilai</option>
              <option value="PJU">Penanggung jawab PJU</option>
              <option value="ADMIN">Admin</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-zinc-400">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>

        <div className="space-y-4 mb-8">
          {permissions.map((perm, idx) => (
            <div key={idx} className="flex items-center justify-between py-1 text-xs">
              <span className="text-zinc-800 font-normal">{perm.label}</span>
              {perm.allowed ? (
                <span className="inline-block px-3 py-1 rounded-md text-[11px] font-semibold bg-[#edf4f0] text-[#1a5b3e]">Diizinkan</span>
              ) : (
                <span className="inline-block px-3 py-1 rounded-md text-[11px] font-semibold bg-[#f4f4f5] text-zinc-400">Terbatas</span>
              )}
            </div>
          ))}
        </div>

        {saveSuccess && (
          <div className="mb-4 p-3 bg-[#edf4f0] border border-[#c5dfd3] rounded-lg text-xs text-[#1a5b3e] flex items-center gap-2">
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            <span>Peran dan hak akses berhasil diperbarui! Mengalihkan...</span>
          </div>
        )}

        <div className="flex items-center justify-end gap-3 pt-2">
          <Link href="/akun-akses" className="px-4 py-2 rounded-lg border border-zinc-200 text-zinc-700 hover:bg-zinc-50 text-xs font-medium transition cursor-pointer">
            Batal
          </Link>
          <button type="button" onClick={handleSave} disabled={saving} className="px-4 py-2 rounded-lg bg-[#1a5b3e] hover:bg-[#164d34] text-white text-xs font-medium transition cursor-pointer shadow-xs disabled:opacity-70 flex items-center gap-2">
            {saving ? ( <span>Menyimpan...</span> ) : ( <span>Simpan akses</span>)}
          </button>
        </div>
      </div>
    </div>
  );
}