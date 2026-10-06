import React from 'react';
import { Button } from './ui/button';
import { X } from 'lucide-react';

export default function Documentation({ onClose }) {
  return (
    <div className="fixed inset-0 z-[2000] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" data-testid="docs-modal"
         onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-card border rounded-lg w-full max-w-4xl flex flex-col" style={{ maxHeight: '90vh' }}>
        <div className="flex items-center justify-between px-6 py-3 border-b shrink-0">
          <h2 className="text-lg font-bold">OptiRoute - Documentation</h2>
          <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0"><X className="w-4 h-4" /></Button>
        </div>
        <div className="overflow-y-auto flex-1 px-6 py-4" style={{ maxHeight: 'calc(90vh - 60px)' }}>
          <div className="max-w-none space-y-6 text-sm">

            <section>
              <h3 className="text-base font-bold mb-2">Cara Kerja Aplikasi / How It Works</h3>
              <p className="text-muted-foreground leading-relaxed">
                OptiRoute adalah sistem optimasi rute distribusi bantuan bencana yang menggunakan data jaringan jalan nyata dari OpenStreetMap (OSM) dikombinasikan dengan algoritma pencarian dan metaheuristik untuk menemukan rute distribusi optimal.
              </p>
              <ol className="space-y-1.5 text-muted-foreground mt-3 list-decimal list-inside">
                <li><strong>Initialize Road Network</strong> - Klik pada peta untuk menentukan titik pusat, atur radius, lalu ambil data jalan dari OpenStreetMap via OSMnx.</li>
                <li><strong>Set Risk Values</strong> - Setiap ruas jalan diberi nilai risiko (0-1). Bisa di-regenerasi secara random.</li>
                <li><strong>Define Start Points (S1, S2, ...)</strong> - Tambahkan titik pengumpulan/gudang dan atur jumlah agent (kendaraan) per titik.</li>
                <li><strong>Define Evacuation Points (E1, E2, ...)</strong> - Tambahkan titik tujuan/pengungsian yang harus menerima bantuan.</li>
                <li><strong>Simulate Blocked Roads</strong> - Klik pada jalan untuk menghapusnya (simulasi jalan rusak). Tanda silang (X) akan muncul.</li>
                <li><strong>Adjust Risk Thresholds</strong> - Atur batas risiko rendah/sedang/tinggi via slider.</li>
                <li><strong>Run Optimization</strong> - Sistem menggunakan VRP solver untuk assign tujuan ke agent dan mencari rute optimal.</li>
                <li><strong>Compare Algorithms</strong> - Bandingkan semua 7 algoritma. Setiap rute ditampilkan dengan warna berbeda di peta.</li>
                <li><strong>Export Results</strong> - Export ke JSON, CSV, atau PNG image.</li>
              </ol>
            </section>

            <section>
              <h3 className="text-base font-bold mb-2">Fungsi Biaya / Cost Function</h3>
              <div className="bg-muted p-3 rounded font-mono text-center">
                <strong>Cost = Distance x (1 + Risk)</strong>
              </div>
              <p className="text-muted-foreground mt-2">
                Dimana Distance = panjang jalan (meter), Risk = nilai bahaya (0-1).<br />
                <strong>Contoh:</strong> Jalan panjang 500m, Risk = 0.4 → Cost = 500 x (1 + 0.4) = <strong>700</strong>
              </p>
            </section>

            <section>
              <h3 className="text-base font-bold mb-2">Algoritma / Algorithms</h3>
              <div className="space-y-3">
                <AlgoDoc name="1. Dijkstra" color="#3B82F6"
                  desc="Menemukan jalur terpendek dengan selalu mengekspansi node dengan cost kumulatif terendah. Menjamin solusi optimal."
                  calc="Diberikan edge A→B (cost 5), A→C (cost 2), C→B (cost 2): Dijkstra eksplorasi C dulu (cost 2), lalu B via C (cost 4), lebih baik dari A→B langsung (cost 5)."
                  complexity="O((V + E) log V)" />
                <AlgoDoc name="2. A* (A-Star)" color="#8B5CF6"
                  desc="Seperti Dijkstra tapi menggunakan heuristik (jarak Euclidean ke target). f(n) = g(n) + h(n), g = cost kumulatif, h = estimasi heuristik."
                  calc="Jika target di timur, A* memprioritaskan node ke timur → eksplorasi lebih sedikit node dari Dijkstra, tetap menemukan jalur optimal."
                  complexity="O((V + E) log V) - biasanya lebih cepat" />
                <AlgoDoc name="3. BFS (Breadth-First Search)" color="#F97316"
                  desc="Eksplorasi semua tetangga di kedalaman saat ini sebelum ke level berikutnya. Tidak mempertimbangkan bobot edge."
                  calc="BFS menemukan path A→B→D (3 hop) sebelum A→C→E→D (4 hop), tanpa memperhitungkan cost. Digunakan sebagai baseline."
                  complexity="O(V + E)" />
                <AlgoDoc name="4. Genetic Algorithm (GA)" color="#22C55E"
                  desc="Pendekatan evolusi: generate populasi solusi rute, evaluasi fitness (1/cost), evolusi melalui seleksi, crossover, dan mutasi."
                  calc="Populasi: [A→B→D, A→C→D]. Crossover di node B: child A→B→C→D. Mutasi: ganti sub-rute. Generasi terbaik bertahan. Parameter: population, generations, mutation rate."
                  complexity="O(pop_size x generations x path_length)" />
                <AlgoDoc name="5. GA + Early Stopping (GA-ES)" color="#06B6D4"
                  desc="Sama dengan GA tapi berhenti ketika tidak ada perbaikan selama N generasi berturut-turut (stagnation limit). Hemat waktu komputasi."
                  calc="Jika stagnation_limit=10 dan best cost tidak membaik selama 10 generasi, algoritma berhenti lebih awal."
                  complexity="Variabel - biasanya lebih cepat dari GA standar" />
                <AlgoDoc name="6. Ant Colony Optimization (ACO)" color="#EF4444"
                  desc="Simulasi perilaku semut. Semut menelusuri graf secara probabilistik berdasarkan level feromon dan cost edge."
                  calc="Edge A→B: feromon=2.0, cost=100. Edge A→C: feromon=1.0, cost=50. Probabilitas ∝ (feromon^α) x (1/cost)^β. Feromon tinggi + cost rendah = probabilitas lebih tinggi."
                  complexity="O(ants x iterations x path_length)" />
                <AlgoDoc name="7. ACO + Early Stopping (ACO-ES)" color="#EC4899"
                  desc="Sama dengan ACO tapi berhenti ketika tidak ada perbaikan selama N iterasi berturut-turut."
                  calc="Jika stagnation_limit=10 dan cost terbaik tidak membaik selama 10 iterasi, berhenti lebih awal."
                  complexity="Variabel" />
              </div>
            </section>

            <section>
              <h3 className="text-base font-bold mb-2">VRP (Vehicle Routing Problem)</h3>
              <p className="text-muted-foreground">
                Ketika ada beberapa titik awal dan agent, OptiRoute menyelesaikan Multi-Depot VRP:
              </p>
              <ol className="space-y-1 text-muted-foreground mt-2 list-decimal list-inside">
                <li>Pre-compute shortest path costs antara semua pasangan start/destination</li>
                <li>Greedy nearest-neighbor assignment: setiap tujuan yang belum ditugaskan diberikan ke agent terdekat</li>
                <li>Untuk setiap agent, hitung rute optimal melalui tujuan yang ditugaskan</li>
                <li>Semua tujuan harus dikunjungi oleh tepat satu agent</li>
              </ol>
            </section>

            <section>
              <h3 className="text-base font-bold mb-2">Fitur Lengkap / Features</h3>
              <ul className="space-y-1 text-muted-foreground list-disc list-inside">
                <li>Data jalan nyata dari OpenStreetMap via OSMnx</li>
                <li>7 algoritma pathfinding dengan parameter yang bisa dikonfigurasi</li>
                <li>Multi-depot Vehicle Routing dengan jumlah agent per depot</li>
                <li>Visualisasi risiko jalan (hijau/kuning/merah) dengan threshold yang bisa diatur</li>
                <li>Simulasi jalan terputus/blok dengan tanda silang (X)</li>
                <li>Klik peta untuk menentukan titik center inisialisasi</li>
                <li>Perbandingan performa algoritma dengan grafik dan tabel</li>
                <li>Rute perbandingan ditampilkan dengan warna berbeda per algoritma</li>
                <li>Export hasil ke JSON, CSV, atau PNG image</li>
                <li>Import session dari file JSON</li>
                <li>Tema Gelap/Terang</li>
                <li>Antarmuka bilingual (English/Indonesian)</li>
              </ul>
            </section>

          </div>
        </div>
      </div>
    </div>
  );
}

function AlgoDoc({ name, color, desc, calc, complexity }) {
  return (
    <div className="border rounded p-3 space-y-1.5" style={{ borderLeftWidth: '3px', borderLeftColor: color }}>
      <h4 className="text-sm font-bold" style={{ color }}>{name}</h4>
      <p className="text-xs text-muted-foreground">{desc}</p>
      <div className="bg-muted/50 rounded p-2">
        <p className="text-[11px] text-muted-foreground"><strong>Perhitungan/Contoh:</strong> {calc}</p>
      </div>
      <p className="text-[10px] font-mono text-muted-foreground">Complexity: {complexity}</p>
    </div>
  );
}
