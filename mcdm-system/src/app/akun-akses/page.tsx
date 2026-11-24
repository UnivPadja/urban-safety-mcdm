"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { AppUserAccount, fetchUsers } from "../../lib/api";
import { ROLE_LABELS } from "../../lib/auth";

export default function AkunAksesPage() {
  const [users, setUsers] = useState<AppUserAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [showPermissionsModal, setShowPermissionsModal] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await fetchUsers();
        setUsers(data);
      } catch {
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="p-8 bg-[#F7F8F5] min-h-full">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 leading-tight">Akun dan akses</h1>
          <p className="text-xs text-zinc-500 mt-1">Kelola akses penilai, penanggung jawab PJU, dan admin.</p>
        </div>

        <button type="button" onClick={() => setShowPermissionsModal(true)} className="px-4 py-2.5 rounded-lg bg-[#1a5b3e] hover:bg-[#164d34] text-white text-xs font-medium flex items-center gap-2 shadow-xs transition cursor-pointer">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
          </svg>
          <span>Kelola izin</span>
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-zinc-200/80 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-100">
          <h2 className="text-[15px] font-bold text-zinc-900">Pengguna</h2>
          <p className="text-xs text-zinc-400 mt-0.5">{loading ? "Memuat..." : `${users.length} akun aktif`}</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-zinc-100 text-zinc-400 font-medium">
                <th className="py-3 px-6">Nama akun</th>
                <th className="py-3 px-4">Peran</th>
                <th className="py-3 px-4">Izin utama</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 text-zinc-700">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-zinc-50/60 transition-colors">
                  <td className="py-4 px-6 font-semibold text-zinc-900 whitespace-nowrap">{user.full_name}</td>
                  <td className="py-4 px-4 text-zinc-600 whitespace-nowrap">{ROLE_LABELS[user.role] || user.role}</td>
                  <td className="py-4 px-4 text-zinc-600 whitespace-nowrap">{user.main_permission || "Kelola data sistem"}</td>
                  <td className="py-4 px-4 whitespace-nowrap">
                    <span className="inline-block px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-[#edf4f0] text-[#1a5b3e] border border-[#c5dfd3]">Aktif</span>
                  </td>
                  <td className="py-4 px-4 whitespace-nowrap">
                    <Link href={`/akun-akses/${user.id}`} className="text-xs text-zinc-700 hover:text-[#1a5b3e] font-medium transition cursor-pointer">
                      Edit &rarr;
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showPermissionsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="w-full max-w-xl bg-white rounded-2xl p-6 shadow-xl border border-zinc-200/80 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#edf4f0] text-[#1a5b3e] flex items-center justify-center">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                  </svg>
                </div>
                <div>
                  <h3 className="text-sm font-bold text-zinc-900">Matriks Hak Akses Peran</h3>
                  <p className="text-[11px] text-zinc-400">Ringkasan izin operasional sistem DSS Jatinangor</p>
                </div>
              </div>
              <button type="button" onClick={() => setShowPermissionsModal(false)} className="text-zinc-400 hover:text-zinc-600 p-1 text-sm cursor-pointer">&times;</button>
            </div>

            <div className="space-y-3 text-xs mb-6">
              <div className="p-3 bg-zinc-50 rounded-xl border border-zinc-100 flex items-start justify-between">
                <div>
                  <p className="font-semibold text-zinc-900">Penilai</p>
                  <p className="text-[11px] text-zinc-500">Mengisi matriks perbandingan berpasangan AHP dan memvalidasi nilai CR.</p>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#edf4f0] text-[#1a5b3e]">Bobot AHP</span>
              </div>
              <div className="p-3 bg-zinc-50 rounded-xl border border-zinc-100 flex items-start justify-between">
                <div>
                  <p className="font-semibold text-zinc-900">Penanggung jawab PJU</p>
                  <p className="text-[11px] text-zinc-500">Input data lapangan/inspeksi, melihat hasil ranking TOPSIS, dan mengunci daftar kerja perbaikan.</p>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#edf4f0] text-[#1a5b3e]">Data & Daftar Kerja</span>
              </div>
              <div className="p-3 bg-zinc-50 rounded-xl border border-zinc-100 flex items-start justify-between">
                <div>
                  <p className="font-semibold text-zinc-900">Admin</p>
                  <p className="text-[11px] text-zinc-500">Mengelola seluruh akun pengguna, penetapan peran, dan izin sistem.</p>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[#edf4f0] text-[#1a5b3e]">Penuh</span>
              </div>
            </div>

            <div className="flex justify-end">
              <button type="button" onClick={() => setShowPermissionsModal(false)} className="px-4 py-2 rounded-lg bg-[#1a5b3e] hover:bg-[#164d34] text-white text-xs font-medium cursor-pointer">Tutup</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}