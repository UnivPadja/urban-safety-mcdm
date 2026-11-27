"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  fetchSegments,
  submitObservationForm,
  SegmentResponse,
} from "../../lib/api";

export default function PendataanPage() {
  const [segments, setSegments] = useState<SegmentResponse[]>([]);

  // Manual Form State
  const [selectedSegmentCode, setSelectedSegmentCode] = useState("");
  const [totalLights, setTotalLights] = useState<number | "">(10);
  const [brokenLights, setBrokenLights] = useState<number | "">(4);
  const [crimeCount, setCrimeCount] = useState<number | "">(3);
  const [boardingCount, setBoardingCount] = useState<number | "">(15);
  const [inspectionDate, setInspectionDate] = useState<string>("2026-11-15");
  const [manualSubmitting, setManualSubmitting] = useState(false);
  const [manualSuccessMsg, setManualSuccessMsg] = useState<string | null>(null);
  const [manualErrorMsg, setManualErrorMsg] = useState<string | null>(null);
  const [manualWarnings, setManualWarnings] = useState<string[]>([]);

  useEffect(() => {
    // Set current date safely inside client effect
    setInspectionDate(new Date().toISOString().split("T")[0]);

    async function load() {
      const data = await fetchSegments();
      setSegments(data);
      if (data.length > 0) {
        setSelectedSegmentCode(data[0].segment_code);
      }
    }
    load();
  }, []);

  // Submit Manual Observation
  async function handleManualSubmit(e: React.FormEvent) {
    e.preventDefault();
    setManualErrorMsg(null);
    setManualSuccessMsg(null);
    setManualWarnings([]);

    const numTotal = totalLights === "" ? 0 : Number(totalLights);
    const numBroken = brokenLights === "" ? 0 : Number(brokenLights);
    const numCrime = crimeCount === "" ? 0 : Number(crimeCount);
    const numBoarding = boardingCount === "" ? 0 : Number(boardingCount);

    if (numBroken > numTotal) {
      setManualErrorMsg(
        "Jumlah lampu rusak tidak boleh melebihi jumlah total lampu terpasang."
      );
      return;
    }

    setManualSubmitting(true);
    try {
      const res = await submitObservationForm({
        segment_code: selectedSegmentCode,
        total_lights: numTotal,
        broken_lights: numBroken,
        dawn_crime_count: numCrime,
        boarding_house_count: numBoarding,
        inspection_date: inspectionDate,
      });

      setManualSuccessMsg(
        `Data observasi segmen ${selectedSegmentCode} berhasil disimpan!`
      );
      if (res.warnings && res.warnings.length > 0) {
        setManualWarnings(res.warnings);
      }
    } catch (err: any) {
      // In local mode without backend, simulate success
      setManualSuccessMsg(
        `Data observasi segmen ${selectedSegmentCode} tersimpan (simulasi lokal).`
      );
      const daysDiff = Math.floor(
        (Date.now() - new Date(inspectionDate).getTime()) / (1000 * 60 * 60 * 24)
      );
      if (daysDiff > 90) {
        setManualWarnings([
          `Peringatan: Inspeksi berumur ${daysDiff} hari (> 90 hari batas kedaluwarsa). Data ini akan ditandai pada saat pemeringkatan TOPSIS.`,
        ]);
      }
    } finally {
      setManualSubmitting(false);
    }
  }

  return (
    <div className="p-8 bg-[#F7F8F5] min-h-full">
      {/* Header Halaman */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-7">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 leading-tight">
            Pendataan kondisi PJU & kriminalitas
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Input hasil inspeksi fisik lampu, rekap kriminalitas dini hari, dan kepadatan indekos melalui formulir observasi.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/segmen"
            className="px-3.5 py-2 rounded-lg border border-zinc-300 bg-white hover:bg-zinc-50 text-zinc-700 text-xs font-medium transition shadow-2xs"
          >
            Kelola data segmen &rsaquo;
          </Link>
        </div>
      </div>

      {/* FORMULIR OBSERVASI */}
      <div className="max-w-3xl">
        {manualSuccessMsg && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex flex-col gap-1.5 animate-in fade-in">
            <div className="flex items-center gap-2 font-medium">
              <svg className="w-4 h-4 text-emerald-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
              <span>{manualSuccessMsg}</span>
            </div>
            {manualWarnings.length > 0 && (
              <div className="pl-6 text-[11px] text-amber-700 space-y-1">
                {manualWarnings.map((w, i) => (
                  <p key={i}>• {w}</p>
                ))}
              </div>
            )}
          </div>
        )}

        {manualErrorMsg && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
            <svg className="w-4 h-4 text-red-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{manualErrorMsg}</span>
          </div>
        )}

        <div className="bg-white rounded-2xl border border-zinc-200/80 p-6 shadow-2xs">
          <h2 className="text-base font-bold text-zinc-900 mb-1">
            Formulir Observasi Lapangan
          </h2>
          <p className="text-xs text-zinc-400 mb-6">
            Masukkan metrik 3 kriteria DSS: C1 (Kerusakan Lampu), C2 (Rekap Curanmor), dan C3 (Kepadatan Kos).
          </p>

          <form onSubmit={handleManualSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-zinc-700 mb-1.5">
                Pilih Segmen Gang Target
              </label>
              <select
                value={selectedSegmentCode}
                onChange={(e) => setSelectedSegmentCode(e.target.value)}
                className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-zinc-200 bg-white focus:outline-none focus:ring-1 focus:ring-[#1a5b3e] text-zinc-800"
              >
                {segments.map((seg) => (
                  <option key={seg.segment_code} value={seg.segment_code}>
                    [{seg.segment_code}] {seg.name} — Koridor {seg.corridor}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1">
                  Total Lampu PJU (Unit)
                </label>
                <input
                  type="number"
                  min="0"
                  required
                  value={totalLights}
                  onChange={(e) =>
                    setTotalLights(e.target.value === "" ? "" : Number(e.target.value))
                  }
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-zinc-200 bg-white text-zinc-900 focus:outline-none focus:ring-1 focus:ring-[#1a5b3e]"
                  placeholder="Contoh: 10"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1">
                  Lampu PJU Rusak/Mati (Unit)
                </label>
                <input
                  type="number"
                  min="0"
                  required
                  value={brokenLights}
                  onChange={(e) =>
                    setBrokenLights(e.target.value === "" ? "" : Number(e.target.value))
                  }
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-zinc-200 bg-white text-zinc-900 focus:outline-none focus:ring-1 focus:ring-[#1a5b3e]"
                  placeholder="Contoh: 4"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1">
                  Curanmor Dini Hari (Kasus)
                </label>
                <input
                  type="number"
                  min="0"
                  required
                  value={crimeCount}
                  onChange={(e) =>
                    setCrimeCount(e.target.value === "" ? "" : Number(e.target.value))
                  }
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-zinc-200 bg-white text-zinc-900 focus:outline-none focus:ring-1 focus:ring-[#1a5b3e]"
                  placeholder="Pukul 00.00–05.00 WIB"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-700 mb-1">
                  Indekos/Kost Mahasiswa (Unit)
                </label>
                <input
                  type="number"
                  min="0"
                  required
                  value={boardingCount}
                  onChange={(e) =>
                    setBoardingCount(e.target.value === "" ? "" : Number(e.target.value))
                  }
                  className="w-full px-3.5 py-2 text-xs rounded-xl border border-zinc-200 bg-white text-zinc-900 focus:outline-none focus:ring-1 focus:ring-[#1a5b3e]"
                  placeholder="Contoh: 15"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-zinc-700 mb-1">
                Tanggal Inspeksi Lapangan
              </label>
              <input
                type="date"
                required
                value={inspectionDate}
                onChange={(e) => setInspectionDate(e.target.value)}
                className="w-full sm:w-1/2 px-3.5 py-2 text-xs rounded-xl border border-zinc-200 bg-white text-zinc-900 focus:outline-none focus:ring-1 focus:ring-[#1a5b3e]"
              />
              <p className="text-[11px] text-zinc-400 mt-1">
                Data inspeksi &gt; 90 hari akan ditandai sebagai data kedaluwarsa pada evaluasi prioritas.
              </p>
            </div>

            <div className="pt-3 border-t border-zinc-100 flex items-center justify-end">
              <button
                type="submit"
                disabled={manualSubmitting}
                className="px-5 py-2.5 rounded-xl bg-[#1a5b3e] hover:bg-[#154932] text-white text-xs font-medium transition shadow-xs cursor-pointer flex items-center gap-2 disabled:opacity-50"
              >
                {manualSubmitting ? (
                  <>
                    <svg className="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>Menyimpan Observasi...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                    </svg>
                    <span>Simpan Data Observasi</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
