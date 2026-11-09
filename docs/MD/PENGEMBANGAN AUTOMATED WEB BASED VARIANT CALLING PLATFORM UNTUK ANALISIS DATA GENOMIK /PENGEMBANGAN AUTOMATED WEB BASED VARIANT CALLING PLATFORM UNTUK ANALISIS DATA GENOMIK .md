# **PENGEMBANGAN AUTOMATED WEB BASED VARIANT CALLING PLATFORM UNTUK ANALISIS DATA GENOMIK**

**Dosen Pengampu:**

Prof. Dr. Eng. Wisnu Ananta Kusuma S.T., M.T.

![](_page_0_Picture_3.jpeg)

### **Disusun Oleh Kelompok GenoSys (3):**

Dhafin Fasya Arifin G0401241017 Rakazaki Putra Hendrawan G0401241056 Yafits Mubarak G0401241001 Muhammad Fattha Akbarsyah G0401241008 Abid Ra'fad Aziz G0401241029

**Paket A - Perangkat Lunak** *Pipeline Variant Calling* **MATA KULIAH PEMBANGUNAN PERANGKAT LUNAK BIOINFORMATIKA**

**PROGRAM STUDI BIOINFORMATIKA FAKULTAS MATEMATIKA DAN ILMU PENGETAHUAN ALAM INSTITUT PERTANIAN BOGOR 2026**

#### **LATAR BELAKANG**

Perkembangan teknologi *Next Generation Sequencing* (NGS) menghasilkan data sekuensing dalam jumlah besar yang dapat dimanfaatkan untuk berbagai kebutuhan analisis genomik. Data tersebut memungkinkan identifikasi variasi genetik dengan membandingkan hasil sekuensing suatu sampel terhadap genom referensi. Salah satu tahapan penting dalam analisis tersebut adalah *variant calling*, yaitu proses identifikasi variasi nukleotida berdasarkan data *sequencing* yang telah dipetakan terhadap *reference genome*. Meskipun memiliki peran penting dalam analisis genomik, proses *variant calling* terdiri atas sejumlah tahapan bioinformatika yang saling bergantung. *Data sequencing* mentah perlu diperiksa kualitasnya, diproses untuk mengurangi artefak atau *sequence* yang tidak diperlukan, dipetakan terhadap genom referensi, kemudian diproses lebih lanjut sebelum dilakukan identifikasi varian. Hasil *variant calling* selanjutnya perlu dievaluasi dan dapat melalui tahap *filtering* sebelum digunakan pada analisis lanjutan.

Dalam praktiknya, tahapan-tahapan tersebut umumnya dijalankan menggunakan berbagai perangkat lunak bioinformatika secara terpisah melalui *command line*. Pengguna perlu memahami format file genomik, parameter masing-masing *tools*, *dependency* setiap proses, struktur direktori, serta hubungan antara *input* dan *output* setiap tahapan. Pendekatan tersebut dapat menjadi kompleks, khususnya bagi pengguna yang belum terbiasa menjalankan *pipeline* bioinformatika secara manual. Selain itu, pengelolaan data selama proses analisis juga menjadi tantangan. File *sequencing* berukuran besar, hasil *alignment*, hasil *variant calling*, serta *output* dari setiap tahapan analisis perlu dikelola secara sistematis. Apabila proses dilakukan secara manual, terdapat risiko kesalahan dalam pengaturan parameter, pemilihan file, pelaksanaan tahapan *pipeline*, maupun pengelolaan hasil analisis. Maka dari itu, diperlukan suatu perangkat lunak yang mampu mengintegrasikan tahapan *variant calling* ke dalam satu *workflow* yang terstruktur dan mudah digunakan. Sistem yang diusulkan tidak hanya berfungsi sebagai antarmuka untuk menjalankan *tools* bioinformatika, tetapi juga mengelola data input, parameter analisis, status proses, output setiap tahapan, serta hasil akhir secara terintegrasi.

Berdasarkan kebutuhan tersebut, kami mengusulkan pengembangan *Automated Web-Based Variant Calling Platform*, yaitu perangkat lunak berbasis web yang dirancang untuk membantu pengguna menjalankan *workflow variant calling* secara terintegrasi. *Platform* ini akan menyediakan antarmuka untuk mengunggah data *sequencing*, mengatur analisis, menjalankan *pipeline*, memantau proses, serta mengakses hasil *variant calling*. Pengembangan dilakukan mengikuti tahapan yang ditetapkan dalam *Term of Reference*, meliputi analisis kebutuhan melalui wawancara dengan *client*, perancangan antarmuka dan arsitektur sistem beserta *pipeline* bioinformatika, pembuatan *prototype*, implementasi basis data,

integrasi *pipeline* dengan *backend* dan antarmuka, pengujian, perbaikan hasil pengujian dan *hosting*, hingga presentasi hasil akhir pengembangan.

#### **RUMUSAN MASALAH**

Perumusan masalah dari proposal ini adalah: (1) Bagaimana mengelola data input, proses analisis, dan hasil analisis *pipeline variant calling* secara terintegrasi dalam satu alur kerja perangkat lunak?; (2) Bagaimana menyediakan antarmuka sederhana yang memungkinkan pengguna menjalankan analisis tanpa perlu mengetik perintah komputer yang rumit?; (3) Bagaimana merancang sistem yang dapat mengintegrasikan antarmuka, basis data, dan *pipeline* bioinformatika sehingga hasil analisis dapat diakses dan dipahami oleh pengguna?.

#### **TUJUAN**

Proposal ini bertujuan mengelola data input, proses analisis, dan hasil analisis *pipeline variant calling* secara terstruktur dalam satu sistem, menyediakan antarmuka yang memudahkan pengguna menjalankan analisis *variant calling* tanpa perlu mengetik perintah *command line* yang rumit, merancang arsitektur sistem yang mengintegrasikan antarmuka, basis data, dan *pipeline* bioinformatika sehingga hasil analisis dapat diakses dan dipahami oleh pengguna, dan menghasilkan perangkat lunak yang dapat diuji dan digunakan sebagai *prototype* sistem analisis *variant calling*.

## **USULAN SOLUSI**

Kami mengusulkan pengembangan *Automated Web-Based Variant Calling Platform* sebagai perangkat lunak berbasis web untuk mengintegrasikan proses analisis *variant calling* dalam satu platform yang terstruktur. *Platform* ini dirancang untuk mempermudah pengguna dalam mengelola data *sequencing* dan menjalankan tahapan analisis tanpa perlu melakukan setiap proses secara manual menggunakan berbagai perangkat lunak secara terpisah. Sistem akan menghubungkan proses pengolahan data dengan *pipeline* bioinformatika sehingga alur analisis dapat dilakukan secara lebih sistematis. Solusi ini diharapkan dapat menjadi *platform* yang praktis dan mudah digunakan untuk mendukung kebutuhan analisis data genomik.

Data yang digunakan sebagai input utama berupa data *sequencing* dalam format FASTQ/FASTQ.GZ yang kemudian diproses melalui rangkaian tahapan *variant calling*. Secara umum, proses tersebut mencakup *quality control*, *preprocessing*, *alignment* terhadap *genome reference*, *variant calling*, dan *filtering* atau anotasi untuk memperoleh kandidat variasi genetik. Setiap tahapan dirancang sebagai bagian dari satu alur kerja yang saling terintegrasi. Hasil akhir analisis

akan menghasilkan informasi *variant calling* berformat VCF yang dapat digunakan untuk analisis lebih lanjut.

*Platform* berbasis web akan menyediakan antarmuka yang memungkinkan pengguna memasukkan data, menjalankan analisis, serta memantau proses *pipeline* secara lebih mudah. Pengguna juga dapat mengakses hasil analisis melalui *platform* sehingga pengelolaan data dan keluaran analisis menjadi lebih terorganisasi. Integrasi antarmuka pengguna dan *pipeline* bioinformatika diharapkan dapat mengurangi kompleksitas penggunaan berbagai *command line tools* secara terpisah.

Pengembangan solusi akan mempertimbangkan kebutuhan fungsional, kelayakan teknis, serta keterbatasan waktu dan sumber daya selama periode proyek. Pemilihan teknologi, perangkat lunak bioinformatika, dan pendekatan implementasi akan ditentukan berdasarkan hasil analisis kebutuhan serta kesesuaiannya dengan tujuan proyek. Proses pengembangan akan dilakukan secara bertahap mulai dari perancangan, implementasi, integrasi, pengujian, hingga penyempurnaan dan *deployment prototype.*

Melalui pengembangan *platform* ini, proses *variant calling* diharapkan menjadi lebih terintegrasi, sistematis, mudah digunakan, dan terdokumentasi. *Platform* tidak hanya menghasilkan keluaran *variant calling*, tetapi juga menyediakan alur analisis yang dapat dipantau dan dikelola oleh pengguna dalam satu sistem. Hasil pengembangan berupa *prototype* perangkat lunak, *pipeline variant calling*, desain antarmuka, serta dokumentasi dan hasil pengujian akan menjadi keluaran utama proyek.

## **RUANG LINGKUP PEKERJAAN**

Untuk menjaga kelayakan dan ketercapaian proyek selama periode pengembangan, pekerjaan dibatasi pada pengembangan *prototype* perangkat lunak untuk *variant calling* dengan input utama berupa data *sequencing* berformat FASTQ/FASTQ.GZ. Sistem difokuskan pada satu *workflow variant calling* yang akan ditentukan melalui *reference genome* yang disesuaikan berdasarkan kebutuhan *pipeline* dan sumber daya yang tersedia setelah proses analisis kebutuhan bersama client. *Prototype* tidak menjamin kompatibilitas dengan seluruh *platform sequencing* dan tidak mencakup analisis data berskala sangat besar atau *distributed computing* untuk kebutuhan produksi. Fitur tambahan di luar fungsi utama akan dipertimbangkan dan diprioritaskan setelah *workflow* utama *variant calling* berhasil diimplementasikan.

## **DELIVERABLES**

Pada akhir proyek, *deliverables* yang dihasilkan berupa *prototype* perangkat lunak *variant calling* berbasis web yang mencakup antarmuka pengguna (*frontend*), *backend*, dan *database* untuk membangun pipeline *variant*

*calling* yang terintegrasi. *Prototype* tersebut dilengkapi dengan *pipeline variant calling* terintegrasi yang mencakup modul *quality control*, *preprocessing* dan *alignment, variant identification*, serta *filtering variant.* Sistem juga menyediakan *result viewer* untuk menampilkan hasil analisis dan menghasilkan *output variant* dalam format VCF.

Selain produk perangkat lunak, *deliverables* proyek mencakup hasil pengujian dan dokumentasi pengembangan, berupa *testing report, source code* aplikasi, serta *version history* sebagai riwayat pengembangan sistem. Dokumentasi yang diserahkan meliputi *user documentation* sebagai panduan penggunaan dan *technical documentation* yang menjelaskan sistem serta *pipeline* yang dikembangkan. Sebagai keluaran akhir, proyek juga mencakup presentasi dan demonstrasi *prototype* untuk menunjukkan fungsi dan hasil implementasi sistem.

# **TIMELINE PENGEMBANGAN**

| Minggu Tahapan Aktivitas              | Target            |
|---------------------------------------|-------------------|
| 1 Pengenalan Proyek dan               |                   |
| Pemahaman                             | ToR,              |
| penentuan                             | solusi,           |
| 2 Software Development Plan Pembagian | tugas,            |
| timeline                              | , target          |
|                                       | Draft requirement |
| 3 Requirement Analysis Analisis       | berbagai          |
| kebutuhan                             | dan use           |
| case                                  | sistem            |
| 4 Penyampaian Requirement             |                   |
| Presentasi                            | hasil             |
| 5 Perancangan Antarmuka Rancangan     |                   |
| tampilan                              | dan               |
| prototipe                             | UI                |
|                                       | UI Prototype      |
| 6 Perancangan Arsitektur &            |                   |
| Arsitektur                            | sistem ,          |
| database,                             | workflow          |
|                                       | System design     |

| 7 Pembuatan Prototipe                  | Membangun        |
|----------------------------------------|------------------|
| prototipe                              | awal             |
|                                        | Prototipe Awal   |
| 8 Implementasi Basis Data I Struktur   | dan              |
|                                        | Database Tahap 1 |
| 9 Implementasi Basis Data II Integrasi | database         |
| dengan                                 | backend          |
| 10 Implementasi Pipeline I Quality     | Control,         |
|                                        | Pipeline Tahap 1 |
| 11 Implementasi Pipeline II Variant    | calling,         |
| integration                            | pipeline         |
| 12 Testing Pengujian                   | fungsi,          |
| integrasi,                             | dan              |
|                                        | Testing report   |
| 13 Improvement and Hosting Perbaikan   | bug dan          |
| penyiapan                              | hosting          |
|                                        | Prototype final  |
| 14 Presentasi Akhir Demonstrasi        | dan              |
|                                        | Final product    |

## **PERSONALIA**

Tim proyek terdiri atas lima anggota dengan pembagian peran sebagai berikut: (1) Dhafin Fasya Arifin selaku *Project Manager*, bertanggung jawab atas perencanaan, koordinasi, monitoring, komunikasi dengan *client*, dan pengawasan proyek; (2) Yafits Mubarak selaku *System Analyst*, bertanggung jawab atas analisis kebutuhan, perancangan sistem, *database*, dan *workflow pipeline*; (3) Abid Ra'fad Aziz selaku *Front-End Developer*, bertanggung jawab atas pengembangan antarmuka dan integrasi *frontend* dengan API; (4) Rakazaki Putra Hendrawan selaku *Back-End Developer*, bertanggung jawab atas pengembangan API, *database*, pengelolaan file, dan integrasi *pipeline*; serta (5) Muhammad Fattha Akbarsyah selaku *Software Tester/Quality Assurance*, bertanggung jawab atas perencanaan dan pelaksanaan pengujian, validasi sistem, pelacakan *bug*, dan dokumentasi hasil pengujian.

## **RANCANGAN ANGGARAN BELANJA**

| No Komponen Keterangan                              | Estimasi     |
|-----------------------------------------------------|--------------|
| 1 Honorarium Project                                |              |
| Koordinasi, monitoring,                             |              |
| komunikasi client                                   |              |
| Rp                                                  | 5.500.000,00 |
| 2 Honorarium System Analyst Analisis kebutuhan,     |              |
| perancangan sistem &                                |              |
| Rp                                                  | 6.500.000,00 |
| 3 Honorarium Front-End                              |              |
| Pengembangan antarmuka &                            |              |
| integrasi API                                       |              |
| Rp                                                  | 6.000.000,00 |
| 4 Honorarium Back-End                               |              |
| Pengembangan API,                                   |              |
| database , integrasi pipeline                       |              |
| Rp                                                  | 6.500.000,00 |
| 5 Honorarium Software                               |              |
| Pengujian, validasi sistem,                         |              |
| dokumentasi uji                                     |              |
| Rp                                                  | 5.500.000,00 |
| 6 Computational resource Cloud compute untuk        |              |
| alignment & variant calling                         |              |
| Rp                                                  | 6.000.000,00 |
| 7 Storage data Penyimpanan data sequencing          |              |
| & hasil analisis                                    |              |
| Rp                                                  | 3.000.000,00 |
| 8 Hosting/deployment Server untuk deployment &      |              |
| demo prototype                                      |              |
| Rp                                                  | 2.000.000,00 |
| 9 Software/service pendukung Version control & task |              |
| management tools                                    |              |
| Rp                                                  | 2.500.000,00 |
| 10 Pengujian Dataset benchmark & uji                |              |
| Rp                                                  | 3.500.000,00 |
| 11 Dokumentasi dan kebutuhan                        |              |
| Penyusunan user & technical                         |              |
| Rp                                                  | 3.000.000,00 |
| TOTAL                                               | Rp           |

# **RISIKO PROYEK**

| No Risiko Dampak                                | Mitigasi      |
|-------------------------------------------------|---------------|
| 1 Ukuran file input besar &                     |               |
| keterbatasan penyimpanan                        |               |
| Proses unggah                                   |               |
| lambat, analisis                                |               |
| terhenti, ruang                                 |               |
| server penuh                                    |               |
| Batasi                                          | ukuran        |
| data                                            | uji untuk     |
| prototipe,                                      | validasi      |
| file                                            | sejak awal,   |
|                                                 | dan hapus     |
|                                                 | otomatis file |
| sementara                                       | setelah       |
|                                                 | hasil akhir   |
| 2 Kesalahan pada basis data Data hasil analisis |               |
| hilang atau tidak                               |               |
| tersimpan dengan                                |               |
| pengecekan                                      | data          |
| serta                                           | pencadangan   |
| secara                                          | berkala       |
| 3 Data masukan tidak valid atau                 |               |
| proses integrasi antar komponen                 |               |
| Pipeline gagal                                  |               |
| berjalan, hasil                                 |               |
| analisis menjadi                                |               |
| tidak akurat, fitur                             |               |
| tidak berfungsi                                 |               |
| pengecekan                                      | data          |
| sejak                                           | awal, serta   |
| integrasi                                       | sebelum       |
| 4 Keterbatasan kemampuan                        |               |
| komputasi server                                |               |
| Proses analisis                                 |               |
| berjalan lama atau                              |               |
| gagal karena                                    |               |
| melebihi waktu                                  |               |
| Jalankan                                        | proses        |
| analisis                                        | secara        |
| terpisah                                        | di latar      |
| belakang,                                       | serta         |
| batasi                                          | ukuran data   |
|                                                 | uji sesuai    |
| kapasitas                                       | server        |
| 5 Pipeline analisis gagal di tengah             |               |
| Analisis terhenti                               |               |
| tanpa keterangan                                |               |
| yang jelas                                      |               |
| pencatatan                                      | log           |
| dan                                             | penanganan    |
|                                                 | kesalahan di  |
|                                                 | setiap tahap  |

| 6 Ketergantungan antar perangkat         |            |
|------------------------------------------|------------|
| lunak/ tools bermasalah                  |            |
| Pipeline tidak                           |            |
| dapat berjalan                           |            |
| Gunakan                                  | sistem     |
| (Docker)                                 | agar       |
| tools                                    | berjalan   |
| dalam                                    | lingkungan |
| yang                                     | konsisten  |
| 7 Terjadi bug pada aplikasi Sistem tidak |            |
| berjalan sesuai                          |            |
| yang diharapkan                          |            |
| pengujian                                | aplikasi   |
| menyeluruh                               | dan        |
| 8 Perubahan kebutuhan di tengah          |            |
| proses pengembangan                      |            |
| Ruang lingkup                            |            |
| bertambah dan                            |            |
| Kunci                                    | kebutuhan  |
| sistem                                   | setelah    |
| tahap                                    | analisis   |
| kebutuhan                                | selesai    |

## **PENUTUP**

Kami mengusulkan pengembangan *Automated Web-Based Variant Calling Platform* sebagai solusi berbasis web untuk mengintegrasikan proses *variant calling* secara terstruktur, mulai dari input *data sequencing*, *quality control*, *preprocessing*, *alignment*, *variant calling*, *filtering*, hingga penyajian hasil. Sistem mencakup *frontend*, *backend*, *database*, *storage*, dan *pipeline* yang saling terintegrasi untuk mengurangi kompleksitas analisis secara manual serta mempermudah pengelolaan data dan hasil analisis. Kami menyatakan kesanggupan melaksanakan pekerjaan sesuai ruang lingkup, *timeline* yang diberikan, *deliverables*, dan target yang telah ditetapkan. Pengembangan dilakukan secara bertahap dengan memprioritaskan *workflow* inti *variant calling* sehingga menghasilkan *prototype* perangkat lunak yang dapat diuji, didokumentasikan, serta mengimplementasikan integrasi rekayasa perangkat lunak dan analisis data genomik.