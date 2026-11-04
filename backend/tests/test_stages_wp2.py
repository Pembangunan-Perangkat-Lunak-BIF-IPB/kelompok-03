"""Pengujian Unit untuk Tahap WP-2 (QC/Trimming, Alignment, BAM Processing).

Menguji kepatuhan terhadap kontrak antarmodul Bagian 3, sanitasi nama sampel,
pemetaan parameter trimming K4, serta alur single-end dan paired-end.
"""
from pathlib import Path
import pytest
from app.pipeline.konteks import Konteks, TahapGagal
from app.pipeline.stages import qc_trimming, alignment, bam_processing


class DummyRunner:
    """Mock runner untuk menguji pembentukan perintah dan alur eksekusi tahap."""
    def __init__(self, simulate_file_creation=True):
        self.commands = []
        self.logs = []
        self.progress_history = []
        self.simulate_file_creation = simulate_file_creation

    def catat(self, pesan, jenis="info"):
        self.logs.append((jenis, pesan))

    def progres(self, persen):
        self.progress_history.append(persen)

    def run(self, cmd, *, stdout=None, stdin_from=None, timeout=None, nama=None):
        self.commands.append((cmd, stdout, nama))
        # Simulasi pembuatan berkas keluaran
        if self.simulate_file_creation:
            if cmd[0] == "fastp":
                # Cari -o dan -O serta -j -h
                for idx, flag in enumerate(cmd):
                    if flag in ("-o", "-O", "-j", "-h") and idx + 1 < len(cmd):
                        p = Path(cmd[idx + 1])
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_text("dummy fastp output")
            elif cmd[0] == "samtools":
                if cmd[1] == "sort":
                    for idx, flag in enumerate(cmd):
                        if flag == "-o" and idx + 1 < len(cmd):
                            p = Path(cmd[idx + 1])
                            p.parent.mkdir(parents=True, exist_ok=True)
                            p.write_text("dummy sorted bam")
                elif cmd[1] == "index":
                    bam_path = Path(cmd[2])
                    Path(str(bam_path) + ".bai").write_text("dummy bai index")
                elif cmd[1] == "flagstat" and stdout:
                    Path(stdout).write_text("100 + 0 in total\n80 + 0 mapped (80.00%)\n")

    def run_pipe(self, cmd1, cmd2, *, nama=None):
        self.commands.append((("PIPE", cmd1, cmd2), None, nama))
        if self.simulate_file_creation:
            # Cari flag -o pada cmd2 (samtools view)
            for idx, flag in enumerate(cmd2):
                if flag == "-o" and idx + 1 < len(cmd2):
                    p = Path(cmd2[idx + 1])
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text("dummy raw bam")


@pytest.fixture
def temp_workspace(tmp_path):
    kerja = tmp_path / "work_1"
    kerja.mkdir(parents=True, exist_ok=True)
    ref = tmp_path / "ref.fasta"
    ref.write_text(">chr1\nACGTACGT\n")
    r1 = tmp_path / "sample_R1.fastq.gz"
    r1.write_text("@r1\nACGT\n+\nIIII\n")
    r2 = tmp_path / "sample_R2.fastq.gz"
    r2.write_text("@r2\nACGT\n+\nIIII\n")
    return {
        "kerja": kerja,
        "ref": ref,
        "r1": r1,
        "r2": r2,
    }


def test_qc_trimming_paired_end(temp_workspace):
    sh = DummyRunner()
    ctx = Konteks(
        id_analisis=1,
        id_sampel=101,
        nama_sampel="Sampel Uji paired",
        kerja=temp_workspace["kerja"],
        referensi=temp_workspace["ref"],
        fastq_r1=temp_workspace["r1"],
        fastq_r2=temp_workspace["r2"],
        parameter={"kualitas_pemangkasan_min": 25},
        threads=4
    )

    qc_trimming.jalankan(ctx, sh)

    assert "reads_r1" in ctx.berkas
    assert "reads_r2" in ctx.berkas
    assert "fastp_json" in ctx.berkas
    assert ctx.berkas["reads_r1"].exists()
    assert ctx.berkas["reads_r2"].exists()

    # Periksa parameter fastp memuat window trimming --cut_right (K4)
    fastp_cmd = sh.commands[0][0]
    assert "--cut_right" in fastp_cmd
    assert "--cut_right_mean_quality" in fastp_cmd
    assert "25" in fastp_cmd


def test_qc_trimming_single_end(temp_workspace):
    sh = DummyRunner()
    ctx = Konteks(
        id_analisis=2,
        id_sampel=102,
        nama_sampel="Sampel Uji single",
        kerja=temp_workspace["kerja"],
        referensi=temp_workspace["ref"],
        fastq_r1=temp_workspace["r1"],
        fastq_r2=None,
        parameter={"kualitas_pemangkasan_min": 20},
        threads=2
    )

    qc_trimming.jalankan(ctx, sh)

    assert "reads_r1" in ctx.berkas
    assert "reads_r2" not in ctx.berkas
    assert ctx.berkas["reads_r1"].exists()


def test_qc_trimming_file_not_found(temp_workspace):
    sh = DummyRunner()
    ctx = Konteks(
        id_analisis=3,
        id_sampel=103,
        nama_sampel="Sampel Hilang",
        kerja=temp_workspace["kerja"],
        referensi=temp_workspace["ref"],
        fastq_r1=Path("/path/tidak/ada/r1.fastq.gz"),
        fastq_r2=None
    )

    with pytest.raises(TahapGagal, match="FASTQ R1 tidak ditemukan"):
        qc_trimming.jalankan(ctx, sh)


def test_alignment_with_rg_sanitization(temp_workspace):
    sh = DummyRunner()
    ctx = Konteks(
        id_analisis=4,
        id_sampel=104,
        nama_sampel="Sampel Bahaya\tTab Spasi;Drop",
        kerja=temp_workspace["kerja"],
        referensi=temp_workspace["ref"],
        fastq_r1=temp_workspace["r1"],
        threads=2,
        berkas={"reads_r1": temp_workspace["r1"]}
    )

    alignment.jalankan(ctx, sh)

    assert "bam_mentah" in ctx.berkas
    # Cek bahwa perintah bwa mem disanitasi tag Read Group-nya (R3)
    pipe_entry = sh.commands[0][0]
    assert pipe_entry[0] == "PIPE"
    cmd_bwa = pipe_entry[1]
    assert "-R" in cmd_bwa
    rg_idx = cmd_bwa.index("-R") + 1
    rg_str = cmd_bwa[rg_idx]
    assert "\tTab" not in rg_str
    assert "Sampel_Bahaya_Tab_Spasi_Drop" in rg_str


def test_bam_processing_sort_index_flagstat(temp_workspace):
    sh = DummyRunner()
    raw_bam = temp_workspace["kerja"] / "dummy_raw.bam"
    raw_bam.write_text("raw bam content")

    ctx = Konteks(
        id_analisis=5,
        id_sampel=105,
        nama_sampel="Sampel Uji",
        kerja=temp_workspace["kerja"],
        referensi=temp_workspace["ref"],
        threads=2,
        berkas={"bam_mentah": raw_bam}
    )

    bam_processing.jalankan(ctx, sh)

    assert "bam" in ctx.berkas
    assert "flagstat" in ctx.berkas
    assert ctx.berkas["bam"].name == "sorted.bam"
    assert ctx.berkas["flagstat"].name == "flagstat.txt"
    assert ctx.berkas["flagstat"].exists()

