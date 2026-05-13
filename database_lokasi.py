# database_lokasi.py
# Data Koordinat Lengkap Kabupaten/Kota di Indonesia (Latitude, Longitude)
# Total: 514 Kabupaten/Kota

indo_coords = {
    # --- ACEH ---
    'banda aceh': [5.5483, 95.3238], 'sabang': [5.8912, 95.3193], 'lhokseumawe': [5.1764, 97.1472], 
    'langsa': [4.4722, 97.9702], 'subulussalam': [2.6333, 97.9833], 'aceh besar': [5.3851, 95.5193],
    'aceh jaya': [4.7500, 95.6500], 'aceh barat': [4.1444, 96.1265], 'aceh barat daya': [3.8300, 96.8500],
    'aceh selatan': [3.3500, 97.2000], 'aceh singkil': [2.4300, 97.9200], 'aceh tenggara': [3.3700, 97.8000],
    'aceh tengah': [4.5100, 96.8500], 'aceh timur': [4.6190, 97.7472], 'aceh utara': [4.9450, 97.1650],
    'bener meriah': [4.7400, 96.8500], 'bireuen': [5.2200, 96.7000], 'gayo lues': [3.9500, 97.3500],
    'nagan raya': [4.1500, 96.3500], 'pidie': [5.1000, 95.9500], 'pidie jaya': [5.1500, 96.1500],
    'simeulue': [2.4500, 96.2500], 'aceh tamiang': [4.2500, 98.0500],

    # --- SUMATERA UTARA ---
    'medan': [3.5951, 98.6722], 'binjai': [3.6026, 98.4855], 'tebing tinggi': [3.3276, 99.1626],
    'pematang siantar': [2.9604, 99.0682], 'tanjung balai': [2.9600, 99.8000], 'sibolga': [1.7397, 98.7834],
    'padang sidempuan': [1.3742, 99.2713], 'gunungsitoli': [1.2833, 97.6167], 'asahan': [2.9800, 99.6200],
    'batubara': [3.1600, 99.5000], 'dairi': [2.8500, 98.2500], 'deli serdang': [3.4907, 98.7107],
    'humbang hasundutan': [2.2500, 98.5000], 'karo': [3.1167, 98.5000], 'labuhanbatu': [2.1500, 99.8300],
    'labuhanbatu selatan': [1.9500, 100.1000], 'labuhanbatu utara': [2.3300, 99.6300], 'langkat': [3.7533, 98.2435],
    'mandailing natal': [0.7500, 99.5000], 'nias': [1.1500, 97.6000], 'nias barat': [1.0500, 97.4500],
    'nias selatan': [0.6000, 97.8500], 'nias utara': [1.3300, 97.3200], 'padang lawas': [1.1500, 99.7500],
    'padang lawas utara': [1.5000, 99.6500], 'pakpak bharat': [2.5500, 98.2500], 'samosir': [2.6000, 98.7000],
    'serdang bedagai': [3.4000, 99.1000], 'simalungun': [2.9000, 99.1000], 'tapanuli selatan': [1.5000, 99.2500],
    'tapanuli tengah': [1.7500, 98.6500], 'tapanuli utara': [2.0000, 99.1000], 'toba': [2.3800, 99.2000],

    # --- SUMATERA BARAT ---
    'padang': [-0.9470, 100.4171], 'bukittinggi': [-0.3054, 100.3692], 'payakumbuh': [0.2241, 100.6315],
    'pariaman': [-0.6256, 100.1207], 'solok': [-0.7937, 100.6586], 'sawahlunto': [-0.6722, 100.7766],
    'padang panjang': [-0.4632, 100.4172], 'agam': [-0.2500, 100.1000], 'dharmasraya': [-1.0500, 101.6000],
    'kepulauan mentawai': [-1.5000, 99.2000], 'lima puluh kota': [0.2000, 100.6500], 'padang pariaman': [-0.6500, 100.2500],
    'pasaman': [0.4000, 100.1000], 'pasaman barat': [0.2000, 99.5000], 'pesisir selatan': [-1.3500, 100.5600],
    'sijunjung': [-0.6500, 101.1500], 'solok selatan': [-1.4500, 101.2000], 'tanah datar': [-0.4500, 100.5800],

    # --- RIAU & KEPRI ---
    'pekanbaru': [0.5070, 101.4477], 'dumai': [1.6702, 101.4442], 'bengkalis': [1.4600, 102.1100],
    'indragiri hilir': [-0.5000, 103.1500], 'indragiri hulu': [-0.5500, 102.3000], 'kampar': [0.3500, 101.2000],
    'kepulauan meranti': [1.0000, 102.7000], 'kuantan singingi': [-0.5000, 101.4500], 'pelalawan': [0.2500, 101.9000],
    'rokan hilir': [2.1500, 100.8000], 'rokan hulu': [0.9000, 100.5000], 'siak': [0.7500, 101.9500],
    'batam': [1.0829, 104.0305], 'tanjungpinang': [0.9169, 104.4533], 'bintan': [1.0800, 104.4800],
    'karimun': [1.0000, 103.3500], 'kepulauan anambas': [3.2000, 106.2000], 'lingga': [-0.2000, 104.6000],
    'natuna': [4.0000, 108.2500],

    # --- JAMBI, BENGKULU, SUMSEL, BABEL ---
    'jambi': [-1.6101, 103.6131], 'sungai penuh': [-2.0500, 101.4000], 'batanghari': [-1.7500, 103.2000],
    'bungo': [-1.5000, 101.9500], 'kerinci': [-2.0800, 101.4000], 'merangin': [-2.1500, 102.1000],
    'muaro jambi': [-1.6000, 103.7500], 'sarolangun': [-2.3000, 102.6500], 'tanjung jabung barat': [-1.1500, 103.2000],
    'tanjung jabung timur': [-1.1000, 104.0000], 'tebo': [-1.4500, 102.4500],
    'bengkulu': [-3.7928, 102.2608], 'bengkulu selatan': [-4.3500, 103.0000], 'bengkulu tengah': [-3.7500, 102.4500],
    'bengkulu utara': [-3.3500, 102.1500], 'kaur': [-4.7000, 103.3500], 'kepahiang': [-3.6500, 102.6000],
    'lebong': [-3.2500, 102.3500], 'mukomuko': [-2.6000, 101.2000], 'rejang lebong': [-3.4500, 102.5500],
    'seluma': [-4.0500, 102.6000],
    'palembang': [-2.9909, 104.7565], 'lubuklinggau': [-3.2952, 102.8611], 'pagar alam': [-4.0205, 103.2323],
    'prabumulih': [-3.4338, 104.2272], 'banyuasin': [-2.8500, 104.3500], 'empat lawang': [-3.7500, 102.9500],
    'lahat': [-3.7800, 103.5500], 'muara enim': [-3.6500, 103.7500], 'musi banyuasin': [-2.7000, 103.8500],
    'musi rawas': [-3.1500, 103.1500], 'musi rawas utara': [-2.5000, 102.9500], 'ogan ilir': [-3.3500, 104.6500],
    'ogan komering ilir': [-3.5500, 105.1500], 'ogan komering ulu': [-4.1000, 104.0500], 'ogan komering ulu selatan': [-4.6000, 104.0000],
    'ogan komering ulu timur': [-3.8500, 104.7000], 'penukal abab lematang ilir': [-3.2000, 104.1000],
    'pangkalpinang': [-2.1306, 106.1105], 'bangka': [-1.9000, 105.9500], 'bangka barat': [-1.7500, 105.3500],
    'bangka selatan': [-2.5000, 106.1000], 'bangka tengah': [-2.3500, 106.2000], 'belitung': [-2.8500, 107.7000],
    'belitung timur': [-2.9000, 108.1500],

    # --- LAMPUNG ---
    'bandar lampung': [-5.4254, 105.2580], 'metro': [-5.1136, 105.3072], 'lampung barat': [-5.0000, 104.1500],
    'lampung selatan': [-5.7000, 105.5000], 'lampung tengah': [-4.9500, 105.1500], 'lampung timur': [-5.1000, 105.6500],
    'lampung utara': [-4.8000, 104.8500], 'mesuji': [-4.0000, 105.4000], 'pesawaran': [-5.4500, 105.1000],
    'pesisir barat': [-5.2000, 103.9500], 'pringsewu': [-5.3500, 104.9500], 'tanggamus': [-5.4000, 104.6500],
    'tulang bawang': [-4.4500, 105.5000], 'tulang bawang barat': [-4.4000, 105.0500], 'way kanan': [-4.5000, 104.6500],

    # --- DKI JAKARTA ---
    'jakarta pusat': [-6.1805, 106.8284], 'jakarta utara': [-6.1214, 106.8741], 'jakarta barat': [-6.1675, 106.7634],
    'jakarta selatan': [-6.2615, 106.8106], 'jakarta timur': [-6.2250, 106.9004], 'kepulauan seribu': [-5.6122, 106.6169],
    'jkt': [-6.2088, 106.8456], 'jakarta': [-6.2088, 106.8456],

    # --- BANTEN ---
    'serang': [-6.1200, 106.1503], 'cilegon': [-6.0174, 106.0201], 'tangerang': [-6.1702, 106.6403],
    'tangerang selatan': [-6.2886, 106.7179], 'lebak': [-6.6346, 106.2238], 'pandeglang': [-6.3084, 106.1062],

    # --- JAWA BARAT ---
    'bandung': [-6.9147, 107.6098], 'bekasi': [-6.2383, 106.9756], 'bogor': [-6.5971, 106.8060],
    'cimahi': [-6.8722, 107.5432], 'cirebon': [-6.7320, 108.5523], 'depok': [-6.4025, 106.7942],
    'sukabumi': [-6.9275, 106.9426], 'tasikmalaya': [-7.3195, 108.2040], 'banjar': [-7.3713, 108.5436],
    'cianjur': [-6.8168, 107.1425], 'garut': [-7.2279, 107.9087], 'indramayu': [-6.3275, 108.3228],
    'karawang': [-6.3227, 107.3113], 'kuningan': [-6.9765, 108.4829], 'majalengka': [-6.8364, 108.2274],
    'pangandaran': [-7.7118, 108.4944], 'purwakarta': [-6.5387, 107.4485], 'subang': [-6.5714, 107.7592],
    'sumedang': [-6.8589, 107.9174],

    # --- JAWA TENGAH ---
    'semarang': [-6.9666, 110.4166], 'salatiga': [-7.3305, 110.5084], 'surakarta': [-7.5666, 110.8166],
    'solo': [-7.5666, 110.8166], 'tegal': [-6.8797, 109.1256], 'pekalongan': [-6.8887, 109.6753],
    'magelang': [-7.4705, 110.2177], 'banjarnegara': [-7.3970, 109.6976], 'banyumas': [-7.5146, 109.2950],
    'batang': [-6.9142, 109.7314], 'blora': [-7.1322, 111.4328], 'boyolali': [-7.5172, 110.5950],
    'brebes': [-6.8690, 109.0435], 'cilacap': [-7.7300, 109.0160], 'demak': [-6.8948, 110.6385],
    'grobogan': [-7.0264, 110.9168], 'jepara': [-6.5861, 110.6674], 'karanganyar': [-7.5959, 111.0049],
    'kebumen': [-7.6672, 109.6515], 'kendal': [-6.9197, 110.2017], 'klaten': [-7.7056, 110.6031],
    'kudus': [-6.8048, 110.8405], 'pati': [-6.7559, 111.0370], 'pemalang': [-6.8893, 109.3807],
    'purbalingga': [-7.3879, 109.3622], 'purworejo': [-7.7126, 110.0091], 'rembang': [-6.7065, 111.3414],
    'sragen': [-7.4267, 111.0222], 'sukoharjo': [-7.6766, 110.8351], 'temanggung': [-7.3134, 110.1718],
    'wonogiri': [-7.8159, 110.9264], 'wonosobo': [-7.3621, 109.9001],

    # --- DIY ---
    'yogyakarta': [-7.7955, 110.3694], 'jogja': [-7.7955, 110.3694], 'bantul': [-7.8887, 110.3289],
    'gunungkidul': [-7.9656, 110.5988], 'kulon progo': [-7.8282, 110.1243], 'sleman': [-7.7306, 110.3481],

    # --- JAWA TIMUR ---
    'surabaya': [-7.2504, 112.7688], 'batu': [-7.8671, 112.5239], 'blitar': [-8.0983, 112.1609],
    'kediri': [-7.8228, 112.0119], 'madiun': [-7.6298, 111.5239], 'malang': [-7.9797, 112.6304],
    'mojokerto': [-7.4726, 112.4338], 'pasuruan': [-7.6449, 112.9033], 'probolinggo': [-7.7554, 113.2159],
    'bangkalan': [-7.0347, 112.7425], 'banyuwangi': [-8.2192, 114.3692], 'bojonegoro': [-7.1502, 111.8818],
    'bondowoso': [-7.9135, 113.8215], 'gresik': [-7.1561, 112.6555], 'jember': [-8.1721, 113.6995],
    'jombang': [-7.5459, 112.2329], 'lamongan': [-7.1185, 112.3150], 'lumajang': [-8.1332, 113.2226],
    'magetan': [-7.6534, 111.3304], 'nganjuk': [-7.5944, 111.9042], 'ngawi': [-7.4042, 111.4429],
    'pacitan': [-8.1965, 111.1099], 'pamekasan': [-7.1633, 113.4795], 'ponorogo': [-7.8687, 111.4646],
    'sampang': [-7.1866, 113.2435], 'sidoarjo': [-7.4478, 112.7183], 'situbondo': [-7.7011, 113.9829],
    'sumenep': [-7.0090, 113.8641], 'trenggalek': [-8.0494, 111.7107], 'tuban': [-6.8966, 112.0632],
    'tulungagung': [-8.0664, 111.9019],

    # --- BALI ---
    'denpasar': [-8.6500, 115.2167], 'badung': [-8.5500, 115.1800], 'bangli': [-8.3500, 115.3500],
    'buleleng': [-8.2000, 115.0000], 'gianyar': [-8.4800, 115.3000], 'jembrana': [-8.3000, 114.6500],
    'karangasem': [-8.4000, 115.5500], 'klungkung': [-8.5500, 115.4000], 'tabanan': [-8.5407, 115.1250],

    # --- NTB & NTT ---
    'mataram': [-8.5833, 116.1166], 'bima': [-8.4542, 118.7247], 'dompu': [-8.5300, 118.4500],
    'lombok barat': [-8.7000, 116.1500], 'lombok tengah': [-8.7500, 116.3000], 'lombok timur': [-8.6500, 116.5500],
    'lombok utara': [-8.3500, 116.2000], 'sumbawa': [-8.5000, 117.4000], 'sumbawa barat': [-8.7500, 116.8500],
    'kupang': [-10.1771, 123.6070], 'alor': [-8.2500, 124.7000], 'belu': [-9.1500, 124.9000],
    'ende': [-8.8436, 121.6622], 'flores timur': [-8.2500, 123.0000], 'lembata': [-8.4000, 123.5000],
    'malaka': [-9.5500, 124.9000], 'manggarai': [-8.5000, 120.4500], 'manggarai barat': [-8.6000, 119.9500],
    'manggarai timur': [-8.6000, 120.6000], 'ngada': [-8.8500, 121.0000], 'nagekeo': [-8.7500, 121.2500],
    'rote ndao': [-10.7500, 123.1500], 'sabu raijua': [-10.5000, 121.8500], 'sikka': [-8.6500, 122.3500],
    'sumba barat': [-9.5500, 119.3500], 'sumba barat daya': [-9.4000, 119.1000], 'sumba tengah': [-9.5000, 119.6500],
    'sumba timur': [-9.8500, 120.3000], 'timor tengah selatan': [-9.8000, 124.4500], 'timor tengah utara': [-9.4500, 124.5500],

    # --- KALIMANTAN BARAT ---
    'pontianak': [-0.0226, 109.3301], 'singkawang': [0.9038, 108.9749], 'bengkayang': [0.8500, 109.5000],
    'kapuas hulu': [0.8500, 112.8000], 'kayong utara': [-1.1500, 110.0000], 'ketapang': [-1.8500, 110.0000],
    'kubu raya': [-0.0100, 109.3500], 'landak': [0.4500, 109.9500], 'melawi': [-0.3500, 111.7000],
    'mempawah': [0.4000, 109.1500], 'sambas': [1.3500, 109.3000], 'sanggau': [0.1500, 110.5500],
    'sekadau': [0.0500, 110.9500], 'sintang': [0.0500, 111.5000],

    # --- KALIMANTAN TENGAH ---
    'palangkaraya': [-2.2161, 113.9145], 'barito selatan': [-1.7500, 114.8500], 'barito timur': [-2.0500, 115.1500],
    'barito utara': [-1.0000, 115.0000], 'gunung mas': [-1.3500, 113.5500], 'kapuas': [-3.0000, 114.3800],
    'katingan': [-2.0500, 113.3500], 'kotawaringin barat': [-2.4000, 111.7500], 'kotawaringin timur': [-2.2000, 112.7500],
    'lamandau': [-2.1500, 111.2500], 'murung raya': [-0.6000, 114.2500], 'pulang pisau': [-2.7500, 114.2000],
    'sukamara': [-2.6500, 111.2000], 'seruyan': [-2.7500, 112.2500],

    # --- KALIMANTAN SELATAN ---
    'banjarmasin': [-3.3166, 114.5901], 'banjarbaru': [-3.4423, 114.8301], 'balangan': [-2.3500, 115.5000],
    'banjar': [-3.4500, 114.9500], 'barito kuala': [-3.0000, 114.6500], 'hulu sungai selatan': [-2.7500, 115.2000],
    'hulu sungai tengah': [-2.6000, 115.4500], 'hulu sungai utara': [-2.4500, 115.2500], 'kotabaru': [-3.2500, 116.2000],
    'tabalong': [-1.9000, 115.4500], 'tanah bumbu': [-3.4500, 115.7000], 'tanah laut': [-3.8500, 114.7500],
    'tapin': [-2.9500, 115.0500],

    # --- KALIMANTAN TIMUR & UTARA ---
    'samarinda': [-0.5022, 117.1536], 'balikpapan': [-1.2379, 116.8528], 'bontang': [0.1260, 117.4700],
    'berau': [2.1500, 117.4800], 'kutai barat': [-0.5000, 115.5500], 'kutai kartanegara': [-0.4200, 116.9800],
    'kutai timur': [1.0500, 117.5000], 'mahakam ulu': [0.5500, 114.7000], 'paser': [-1.8500, 116.0000],
    'penajam paser utara': [-1.2500, 116.6500], 'tarakan': [3.3274, 117.5872], 'bulungan': [2.8500, 117.3500],
    'malinau': [3.0000, 115.5000], 'nunukan': [4.1000, 117.0000], 'tana tidung': [3.5500, 117.0500],

    # --- SULAWESI UTARA & GORONTALO ---
    'manado': [1.4748, 124.8420], 'bitung': [1.4447, 125.1215], 'kotamobagu': [0.7222, 124.3129],
    'tomohon': [1.3323, 124.8385], 'bolaang mongondow': [0.7500, 124.1000], 'bolaang mongondow selatan': [0.3500, 123.9000],
    'bolaang mongondow timur': [0.7000, 124.5000], 'bolaang mongondow utara': [0.8500, 123.3500], 'kepulauan sangihe': [3.5000, 125.5000],
    'kepulauan sitaro': [2.4000, 125.4000], 'kepulauan talaud': [4.3000, 126.7500], 'minahasa': [1.3000, 124.9000],
    'minahasa selatan': [1.1500, 124.6000], 'minahasa tenggara': [1.0500, 124.7500], 'minahasa utara': [1.4500, 125.0000],
    'gorontalo': [0.5435, 123.0568], 'boalemo': [0.6500, 122.3500], 'bone bolango': [0.5500, 123.2000],
    'pohuwato': [0.5000, 121.8000], 'gorontalo utara': [0.8500, 122.7500],

    # --- SULAWESI TENGAH & BARAT ---
    'palu': [-0.8917, 119.8707], 'banggai': [-1.4500, 123.0000], 'banggai kepulauan': [-1.6000, 123.2500],
    'banggai laut': [-1.8000, 123.5000], 'buol': [1.0000, 121.3500], 'donggala': [-0.5500, 119.8500],
    'morowali': [-2.0500, 121.5000], 'morowali utara': [-1.8500, 121.3000], 'parigi moutong': [-0.8500, 120.2500],
    'poso': [-1.4000, 120.7500], 'tojo una-una': [-1.1500, 121.5000], 'toli-toli': [1.0500, 120.8000],
    'mamuju': [-2.6775, 118.8919], 'majene': [-3.1500, 118.9000], 'mamasa': [-2.9000, 119.3000],
    'mamuju tengah': [-2.3000, 119.3500], 'mamuju utara': [-1.3500, 119.3500], 'polewali mandar': [-3.4000, 119.2000],

    # --- SULAWESI SELATAN & TENGGARA ---
    'makassar': [-5.1476, 119.4327], 'palopo': [-2.9926, 120.1942], 'parepare': [-4.0102, 119.6318],
    'bantaeng': [-5.5000, 119.9500], 'barru': [-4.4500, 119.7000], 'bone': [-4.5500, 120.2500],
    'bulukumba': [-5.5500, 120.2000], 'enrekang': [-3.5500, 119.8500], 'gowa': [-5.3500, 119.6500],
    'jeneponto': [-5.6500, 119.7500], 'kepulauan selayar': [-6.1000, 120.5000], 'luwu': [-2.9500, 120.1500],
    'luwu timur': [-2.5500, 121.2000], 'luwu utara': [-2.5000, 120.2500], 'maros': [-5.0000, 119.6000],
    'pangkajene dan kepulauan': [-4.8000, 119.6000], 'pinrang': [-3.8000, 119.6500], 'sidenreng rappang': [-3.9000, 119.9000],
    'sinjai': [-5.2000, 120.1500], 'soppeng': [-4.3500, 119.9500], 'takalar': [-5.4500, 119.4500],
    'tana toraja': [-3.0500, 119.8500], 'toraja utara': [-2.9500, 119.9000], 'wajo': [-4.0000, 120.1500],
    'kendari': [-3.9985, 122.5126], 'baubau': [-5.4674, 122.6046], 'bombana': [-4.7000, 121.8000],
    'buton': [-5.1500, 122.8500], 'buton selatan': [-5.5500, 122.7000], 'buton tengah': [-5.3500, 122.4500],
    'buton utara': [-4.7500, 123.0000], 'kolaka': [-4.0500, 121.6000], 'kolaka timur': [-4.0000, 121.9000],
    'kolaka utara': [-3.3000, 121.0000], 'konawe': [-3.8500, 122.2500], 'konawe kepulauan': [-4.0500, 123.0000],
    'konawe selatan': [-4.2500, 122.4500], 'konawe utara': [-3.4500, 122.1500], 'muna': [-4.8500, 122.5000],
    'muna barat': [-4.8000, 122.3500], 'wakatobi': [-5.3500, 123.5500],

    # --- MALUKU & MALUKU UTARA ---
    'ambon': [-3.6954, 128.1814], 'tual': [-5.6333, 132.7333], 'buru': [-3.4000, 126.7500],
    'buru selatan': [-3.7500, 126.7500], 'kepulauan aru': [-6.1500, 134.5000], 'kepulauan tanimbar': [-7.9000, 131.3000],
    'maluku barat daya': [-8.1500, 127.8500], 'maluku tengah': [-3.3500, 128.9500], 'maluku tenggara': [-5.7500, 132.7500],
    'seram bagian barat': [-3.1500, 128.3000], 'seram bagian timur': [-3.2500, 130.4000],
    'ternate': [0.7893, 127.3753], 'tidore kepulauan': [0.6500, 127.4000], 'halmahera barat': [1.3500, 127.5000],
    'halmahera selatan': [-0.6500, 127.5000], 'halmahera tengah': [0.5000, 128.1000], 'halmahera timur': [1.1500, 128.4500],
    'halmahera utara': [1.5500, 128.0000], 'kepulauan sula': [-1.9000, 125.8500], 'pulau morotai': [2.3000, 128.3000],
    'pulau taliabu': [-1.8000, 124.6500],

    # --- PAPUA (SELURUH WILAYAH) ---
    'jayapura': [-2.5337, 140.7186], 'asmat': [-5.5000, 138.5000], 'biak numfor': [-1.1500, 136.0000],
    'boven digoel': [-6.1000, 140.3000], 'deiyai': [-3.9500, 136.1500], 'dogiyai': [-4.0500, 135.9000],
    'intan jaya': [-3.4500, 137.0000], 'jayawijaya': [-4.0500, 139.0000], 'keerom': [-3.3000, 140.7500],
    'kepulauan yapen': [-1.7500, 136.2500], 'lanny jaya': [-3.9500, 138.3500], 'mappi': [-6.5000, 139.3000],
    'mamberamo raya': [-2.2000, 137.8500], 'mamberamo tengah': [-3.6000, 139.3000], 'merauke': [-8.4991, 140.3995],
    'mimika': [-4.5500, 136.6000], 'nabire': [-3.3661, 135.4975], 'nduga': [-4.4000, 138.1500],
    'paniai': [-3.8500, 136.3500], 'pegunungan bintang': [-4.8000, 140.5000], 'puncak': [-3.8000, 137.5500],
    'puncak jaya': [-3.6500, 137.9000], 'sarmi': [-2.0000, 139.0000], 'supiori': [-0.7500, 135.5500],
    'tolikara': [-3.6000, 138.5500], 'waropen': [-2.4500, 136.7000], 'yahukimo': [-4.5000, 139.5000],
    'yalimo': [-3.8500, 139.4500], 'sorong': [-0.8756, 131.2558], 'fakfak': [-2.9238, 132.2965],
    'kaimana': [-3.6500, 133.7500], 'manokwari': [-0.8615, 134.0620], 'manokwari selatan': [-1.3500, 134.1000],
    'maybrat': [-1.2500, 132.4500], 'pegunungan arfak': [-1.1500, 133.9000], 'raja ampat': [-0.2500, 130.8500],
    'sorong selatan': [-1.5000, 132.2000], 'tambrauw': [-0.6500, 132.5000], 'teluk bintuni': [-2.1500, 133.5000],
    'teluk wondama': [-2.7000, 134.5000],
}