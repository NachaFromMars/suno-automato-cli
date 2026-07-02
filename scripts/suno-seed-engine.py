#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, random, re, subprocess, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'suno-library'

IDEA_BANK = [
  ('broken compass', 'la bàn nứt chỉ về một ký ức chưa đặt tên', 'navigation, fate'),
  ('glass orchard', 'vườn cây bằng kính nở trái ánh đèn', 'fragile beauty, refraction'),
  ('subway temple', 'ngôi chùa nằm dưới đường tàu điện cuối phố', 'urban sacred, underground'),
  ('paper dragon', 'con rồng giấy ngủ trong hộc bàn cũ', 'childhood myth, hidden power'),
  ('radio ghost', 'bóng ma trong chiếc radio chỉ phát lúc bình minh', 'memory, signal, dawn'),
  ('salt lantern', 'đèn lồng muối treo bên bờ biển vắng', 'ocean, healing, burn'),
  ('clock market', 'khu chợ bán những chiếc đồng hồ biết nói dối', 'time, bargain, illusion'),
  ('iron butterfly', 'cánh bướm sắt bay qua lò luyện mưa', 'strength, grace, transformation'),
  ('moon elevator', 'thang máy lên mặt trăng kẹt giữa tầng mây', 'aspiration, suspense'),
  ('ink river', 'dòng sông mực chảy qua những lá thư chưa gửi', 'letters, confession, flow'),
  ('velvet storm', 'cơn bão nhung cuộn trong một phòng hát đỏ', 'drama, softness, force'),
  ('copper forest', 'khu rừng đồng ngân lên khi có người nhớ nhà', 'resonance, homesickness'),
  ('solar teacup', 'tách trà nhỏ giữ một mặt trời riêng', 'domestic cosmic, warmth'),
  ('mirror harbor', 'bến cảng soi gương cho những con tàu lạc', 'return, identity, water'),
  ('amber cathedral', 'nhà thờ hổ phách giữ ánh sáng ba trăm năm', 'preservation, sacred light'),
  ('origami volcano', 'ngọn núi lửa gấp bằng giấy bắt đầu run', 'latent fury, delicate power'),
  ('cassette river', 'dòng sông chảy bằng tiếng băng cát xét cũ', 'analog nostalgia, current'),
  ('porcelain thunder', 'tiếng sấm vang trong chén sứ trắng', 'refined violence, contrast'),
  ('bamboo satellite', 'vệ tinh tre quay quanh một giấc mơ quê', 'tradition meets orbit'),
  ('fog piano', 'cây đàn piano tan dần trong sương mù', 'dissolving melody, mystery'),
  ('rust garden', 'khu vườn rỉ sét nở hoa sau cơn mưa axit', 'toxic bloom, resilience'),
  ('lantern whale', 'con cá voi mang đèn lồng bơi qua phố ngập', 'surreal flood, gentle giant'),
  ('silk earthquake', 'trận động đất bằng lụa lay giấc ngủ trưa', 'gentle upheaval, fabric'),
  ('crystal beehive', 'tổ ong pha lê giữ mật từ ánh trăng', 'harvest moonlight, fragile colony'),
  ('sandpaper lullaby', 'bài hát ru bằng giấy nhám cho đứa trẻ thép', 'rough tenderness, industrial'),
  ('tobacco constellation', 'chòm sao vẽ bằng khói thuốc trên mái hiên', 'late night map, ephemeral'),
  ('marble tide', 'thủy triều bằng đá cẩm thạch dâng lên bậc thềm', 'monumental flow, weight'),
  ('vinyl monsoon', 'mùa mưa quay trên đĩa than cũ kỹ', 'seasonal groove, crackle'),
  ('charcoal sunrise', 'bình minh vẽ bằng than trên tường nhà kho', 'raw art, industrial dawn'),
  ('sugar fortress', 'pháo đài đường tan dần khi trời nóng', 'sweet defense, impermanence'),
  ('titanium cradle', 'chiếc nôi titan ru giấc cho thế hệ sao', 'future nurture, cold warmth'),
  ('pollen bridge', 'cây cầu bằng phấn hoa nối hai mùa', 'seasonal passage, fragile link'),
  ('mercury library', 'thư viện thủy ngân giữ sách viết bằng giấc mơ', 'liquid knowledge, toxic beauty'),
  ('wax cathedral', 'nhà thờ bằng sáp chảy dần khi ca đoàn hát', 'melting sacred, voice heat'),
  ('bone flute', 'ống sáo xương ngân lên giữa cánh đồng tro', 'primal music, aftermath'),
  ('spider silk highway', 'xa lộ tơ nhện nối giữa hai tòa nhà bỏ hoang', 'fragile infrastructure, abandon'),
  ('ember dictionary', 'cuốn từ điển than hồng chỉ đọc được trong đêm', 'glowing knowledge, darkness'),
  ('jade monsoon', 'mùa mưa ngọc bích rơi xuống ruộng muối', 'precious rain, salt earth'),
  ('smoke accordion', 'chiếc đàn accordion khói vang lên trong ga tàu vắng', 'travel melancholy, texture'),
  ('tungsten lullaby', 'bài ru bằng dây vonfram nóng đỏ', 'industrial tenderness, glow'),
  ('fossil radio', 'đài phát thanh hóa thạch phát sóng từ kỷ băng hà', 'ancient broadcast, ice age'),
  ('coral typewriter', 'máy đánh chữ san hô gõ thư dưới đáy biển', 'undersea correspondence'),
  ('obsidian garden', 'khu vườn đá đen nở hoa chỉ khi có sấm', 'volcanic bloom, dark fertile'),
  ('paper monsoon', 'mùa mưa giấy rơi từ máy in của trời', 'printed weather, narrative'),
  ('tin cathedral', 'nhà thờ thiếc vang lên khi mưa đá gõ', 'percussive sacred, weather music'),
  ('amber submarine', 'tàu ngầm hổ phách lặn qua ký ức đông cứng', 'preserved journey, amber time'),
  ('clockwork meadow', 'đồng cỏ máy móc mọc hoa theo nhịp giây', 'mechanical nature, precision bloom'),
  ('lightning pottery', 'bình gốm sét nứt ra ánh sáng khi đêm xuống', 'cracked radiance, handmade'),  ('granite lullaby', 'bài ru bằng đá granit vang trong hẻm núi', 'mountain echo, weight'),
  ('helium kite', 'con diều khí heli kéo đứa trẻ bay khỏi mái nhà', 'childhood escape, lightness'),
  ('cedar telegraph', 'cây tuyết tùng gửi điện tín qua rễ', 'root communication, patience'),
  ('gasoline rainbow', 'cầu vồng xăng loang trên vũng nước sân ga', 'urban iridescence, pollution beauty'),
  ('chalk constellation', 'chòm sao phấn vẽ trên sân trường cũ', 'schoolyard cosmos, innocence'),
  ('copper monsoon', 'mùa mưa đồng xanh rỉ trên mái tôn', 'oxidation, seasonal change'),
  ('paper submarine', 'tàu ngầm giấy lặn vào bể cá trong phòng ngủ', 'miniature adventure, bedroom ocean'),
  ('basalt piano', 'phím đàn bằng đá bazan nóng từ lòng đất', 'volcanic music, deep heat'),
  ('thistle crown', 'vương miện gai bồ công anh đội cho gió', 'wild royalty, dispersal'),
  ('pewter dawn', 'bình minh thiếc xám mở cửa xưởng rèn', 'industrial morning, forge'),
  ('lotus engine', 'động cơ sen quay bằng nước mưa chùa', 'sacred mechanics, green energy'),
  ('cinnamon archive', 'kho lưu trữ quế giữ mùi hương ba đời', 'spice memory, generational'),
  ('driftwood sonata', 'bản sonata gỗ trôi vang trên bãi biển vắng', 'ocean composition, found music'),
  ('asphalt meadow', 'đồng cỏ nhựa đường mọc hoa dại giữa nứt', 'urban wildflower, crack beauty'),
  ('platinum whisper', 'lời thì thầm bạch kim rơi trong phòng kín', 'precious quiet, sealed room'),
  ('monsoon typewriter', 'máy đánh chữ mùa mưa gõ bằng giọt nước', 'weather writing, liquid words'),
  ('saffron blizzard', 'trận bão tuyết nghệ tây nhuộm vàng cả thung lũng', 'spice storm, golden white'),
  ('telegraph vine', 'dây leo điện tín mọc dọc cột điện cũ', 'organic transmission, overgrown'),
  ('indigo furnace', 'lò nung chàm xanh đốt giấc mơ thành gốm', 'dye fire, dream pottery'),
  ('dandelion radar', 'ra đa bồ công anh quét gió tìm mùa', 'seed detection, seasonal scan'),
  ('turquoise avalanche', 'trận lở ngọc lam tuôn xuống sườn đồi khô', 'gem flood, arid beauty'),
  ('molasses clock', 'đồng hồ mật mía chạy chậm hơn thời gian', 'sweet delay, thick time'),
  ('paraffin diary', 'nhật ký nến viết bằng ánh lửa tan', 'wax writing, ephemeral record'),
  ('nettle symphony', 'bản giao hưởng tầm ma ngứa ran trong gió', 'stinging music, wild orchestra'),
  ('vermillion tide', 'thủy triều son đỏ dâng lên bờ cát trắng', 'color flood, dramatic shore'),
  ('lichen telegraph', 'địa y gửi tin nhắn qua bề mặt đá', 'slow message, geological patience'),
  ('feldspar lullaby', 'bài ru tràng thạch vang trong hang đá', 'mineral comfort, cave echo'),
  ('cardamom bridge', 'cây cầu bạch đậu khấu nối hai ngôi làng mù sương', 'spice passage, fog village'),
  ('magnesium bloom', 'bông hoa magiê cháy sáng rồi tắt trong đêm lễ', 'bright burn, ceremony'),
  ('oyster moonrise', 'trăng lên từ vỏ hàu mở giữa bãi bùn', 'pearl birth, tidal timing'),
  ('burlap cathedral', 'nhà thờ vải bố thở theo nhịp gió đồng', 'humble sacred, breathing fabric'),
  ('terracotta storm', 'cơn bão đất nung cuốn mùi mưa đầu mùa', 'earthen fury, petrichor'),
  ('clover engine', 'động cơ cỏ ba lá chạy bằng may mắn', 'luck machine, green fuel'),
  ('sulfur horizon', 'đường chân trời lưu huỳnh vàng cháy sau nhà máy', 'chemical sunset, industrial'),
  ('vanilla tremor', 'cơn chấn nhẹ vani lay chiếc bánh đang nướng', 'sweet earthquake, kitchen'),
  ('sisal hammock', 'võng sợi thùa treo giữa hai ngọn núi', 'elevated rest, mountain gap'),
  ('zinc river', 'dòng sông kẽm bạc chảy qua xóm lò rèn', 'metallic flow, craft village'),
  ('camphor library', 'thư viện long não giữ sách không bao giờ mốc', 'preserved knowledge, aroma shield'),
  ('pumice raft', 'chiếc bè đá bọt trôi trên hồ nước nóng', 'floating stone, volcanic lake'),
  ('amaranth engine', 'động cơ rau dền đỏ quay bằng gió chiều', 'grain power, sunset wind'),
  ('birch telegram', 'bạch dương gửi điện tín qua vỏ trắng bóc', 'bark message, peeling truth'),
  ('rattan telescope', 'kính viễn vọng mây tre nhìn thấy sao bằng mắt bà', 'grandmother astronomy'),
  ('quartz lullaby', 'bài ru thạch anh rung nhẹ trong lòng đất', 'crystal hum, subterranean'),
  ('turmeric monsoon', 'mùa mưa nghệ vàng nhuộm cả con kênh', 'golden rain, canal gold'),
  ('cobalt meadow', 'đồng cỏ coban xanh phát sáng dưới trăng', 'blue glow, moonlit field'),
  ('jute cathedral', 'nhà thờ bằng sợi đay vang tiếng kinh đan', 'woven sacred, textile prayer'),
  ('maple telegraph', 'cây phong gửi lá vàng làm thư mùa thu', 'autumn mail, leaf letter'),
  ('cassava engine', 'động cơ khoai mì chạy bằng bột quê nhà', 'root fuel, homeland starch'),
  ('alabaster tide', 'thủy triều thạch cao trắng dâng lên bậc đền', 'white flood, temple steps'),
  ('allspice blizzard', 'trận bão hương liệu cuốn qua khu chợ nổi', 'floating market storm, spice wind'),
  ('lemongrass radar', 'ra đa sả chanh quét tìm mùi nhớ nhà', 'herbal detection, homesick scan'),
  ('teak submarine', 'tàu ngầm gỗ tếch lặn vào giấc mơ ông ngoại', 'grandfather dream dive'),
  ('coconut telegraph', 'cây dừa gửi tín hiệu qua tiếng gió biển', 'island communication, coastal'),
  ('mango cathedral', 'nhà thờ xoài chín vàng vang mùi ngày hè', 'tropical sacred, summer fruit'),
  ('laterite lullaby', 'bài ru đất đỏ bazan vang trên cao nguyên', 'highland soil song, volcanic'),
  ('bamboo telegraph', 'cây tre gõ nhịp gửi tin qua bờ ruộng', 'rice field morse, rural network'),
  ('tamarind clock', 'đồng hồ me chua đếm giờ bằng vị chua ngọt', 'sour-sweet time, tropical'),
  ('jackfruit engine', 'động cơ mít chín quay bằng mùi thơm lừng', 'tropical fruit power, aroma'),
  ('dragon fruit horizon', 'đường chân trời thanh long hồng cháy sau ruộng', 'exotic sunset, farm'),
  ('starfruit bridge', 'cây cầu khế vắt ngang dòng sông trăng', 'sour crossing, moonlit river'),

]

GENRE_DNA = {
 'Rap': {'bpm':'88-98 BPM', 'groove':'syncopated boom-bap/trap hybrid', 'vocal':'charismatic male rap, internal rhyme, breath-marked double-time bursts', 'prod':'dry punchy drums, 808 glide, dusty saturation, cinematic ad-libs'},
 'Rock': {'bpm':'145-165 BPM', 'groove':'live-band hard rock drive', 'vocal':'raspy chest voice, gang shout hook, controlled screamed accents', 'prod':'drop-D guitars, overdriven bass, huge kick/snare, analog grit'},
 'Pop': {'bpm':'110-124 BPM', 'groove':'radio-ready synth/city-pop groove', 'vocal':'breathy lead, stacked harmonies, crisp melodic hook', 'prod':'sidechained synth bass, glossy plucks, wide chorus master'},
 'Ballad': {'bpm':'68-78 BPM', 'groove':'slow cinematic 6/8 or rubato pulse', 'vocal':'intimate fragile vocal, vibrato, belted final chorus', 'prod':'felt piano, cello, soft string swell, warm room reverb'},
 'EDM': {'bpm':'124 or 148-152 BPM', 'groove':'progressive house/future bass build-drop architecture', 'vocal':'ethereal topline, chopped vocal hook, pre-drop chant', 'prod':'sub sidechain, supersaws, risers, crisp hats, festival master'},
 'Lofi': {'bpm':'76-84 BPM', 'groove':'lazy swung lo-fi bedroom groove', 'vocal':'soft half-sung intimate vocal, humming hook', 'prod':'MPC dust, Rhodes, vinyl crackle, rounded bass, close cozy mix'},
 'Thien': {'bpm':'52-60 BPM', 'groove':'breath-paced meditative pulse', 'vocal':'serene mantra vocal, airy choir response', 'prod':'singing bowls, bamboo flute, temple bell, low drone, huge clean reverb'},
 'Phat-Phap': {'bpm':'66-76 BPM', 'groove':'ritual folk chant pulse', 'vocal':'calm chant lead, soft choir response', 'prod':'wooden fish, temple bell, đàn tranh/đàn bầu, reverent acoustic mix'},
 'Cinematic': {'bpm':'88-98 BPM', 'groove':'massive trailer pulse or martial 6/8', 'vocal':'heroic choir, soaring female ad-libs, chant layers', 'prod':'taiko, brass, low strings, sub impacts, colossal reverb'},
 'Remix-Cover': {'bpm':'116-132 BPM', 'groove':'UK garage/nu-disco remix bounce', 'vocal':'silky lead, chopped hook refrain', 'prod':'rubber sub bass, skippy drums, nostalgic sample texture, club-clean master'},
 'Experimental': {'bpm':'84-94 BPM', 'groove':'fractured trip-hop/broken-beat pulse', 'vocal':'surreal spoken-sung lead, glitch ad-libs, alien choir hook', 'prod':'prepared piano, granular synth, found percussion, clean low-end'},
 'Other': {'bpm':'100-108 BPM', 'groove':'global fusion rolling groove', 'vocal':'joyful unisex lead, communal chorus response', 'prod':'handpan, đàn bầu, talking drum, sunny organic master'},
 'Instrumental': {'bpm':'64-76 BPM', 'groove':'instrumental cinematic pulse', 'vocal':'featured melodic instrument lead, no singer described because Instrumental switch is enabled', 'prod':'felt piano, strings, bamboo flute, subtle percussion, emotional instrumental arc'},
 'Relax-Sleep': {'bpm':'48-54 BPM', 'groove':'sleep ambient breath pulse', 'vocal':'lead texture is pads and bowls, no singer described because Instrumental switch is enabled', 'prod':'warm drones, ocean/forest field recordings, singing bowls, seamless slow fade'},
 'Opera': {'bpm':'70-78 BPM', 'groove':'grand operatic adagio or 3/4 aria', 'vocal':'dramatic soprano/mezzo/tenor response, powerful vibrato, choir lift', 'prod':'full strings, timpani, harp, organ/brass, cathedral reverb'},
 'Cai-Luong': {'bpm':'72-92 BPM', 'groove':'southern Vietnamese cải lương theatre pulse, rubato vọng cổ phrasing', 'vocal':'expressive cải lương lead, ornamented vibrato, spoken-sung dramatic bends', 'prod':'đàn kìm, đàn tranh, đàn bầu glissando, light percussion, theatre ambience'},
 'Bolero': {'bpm':'70-82 BPM', 'groove':'classic Vietnamese bolero 4/4 slow dance sway', 'vocal':'warm sentimental lead, clear diction, gentle vibrato, nostalgic phrasing', 'prod':'nylon guitar arpeggio, accordion/strings, brushed drums, warm bass, analog reverb'},
 'Thieu-Nhi': {'bpm':'100-125 BPM', 'groove':'playful children song bounce, simple clap rhythm', 'vocal':'bright child lead or children choir, playful call-and-response, easy singalong hook', 'prod':'ukulele, xylophone, handclaps, toy piano, light drums, sunny mix'},
 'Restaurant-Jazz-Instrument': {'bpm':'72-96 BPM', 'groove':'elegant restaurant lounge jazz swing or bossa pocket', 'vocal':'featured melodic instrument lead, no singer described because Instrumental switch is enabled', 'prod':'grand piano, upright bass, brushed drums, warm sax or hollow-body guitar, intimate room reverb'},
 'Cinematic-MaxMax': {'bpm':'90-110 BPM', 'groove':'maximum-impact cinematic trailer pulse, hybrid orchestral/electronic war rhythm', 'vocal':'massive mixed choir, heroic soprano ad-libs, low male chant layers', 'prod':'taiko, braams, brass stabs, low string ostinato, sub impacts, risers, colossal 3D master'},
}

HOOK_SHAPES = [
 'repeat title twice with a changed second line',
 'call-and-response hook with two short answering phrases',
 'mantra hook: 4 compact vowel-rich lines',
 'anthem hook: title first, consequence second, emotional release third',
 'question-answer hook: one question, two answers, one twist',
]
RHYME_TEXTURES = ['AABB end rhyme + internal rhyme', 'ABAB slant rhyme', 'free bridge with echo rhyme', 'short vowel-rich hook endings', 'rap multisyllable rhyme clusters']
ARRANGEMENTS = ['dry intro → restrained verse → pre-lift → wide chorus → stripped bridge → final lift', 'motif intro → verse adds bass → chorus doubles vocal → bridge removes drums → final chorus adds counterline', 'cold open hook → verse story → drop/chorus → half-time bridge → outro motif']


LYRIC_CRAFT_TECHNIQUES = [
 'object writing: start from one concrete object and use sight, sound, touch, smell, movement',
 'show-dont-tell verse: specific scene first, emotion implied later',
 'title frame: title appears first and last line of chorus with a changed meaning',
 'rule of three hook: repeat hook twice, twist the third repetition',
 'call-response chorus: lead line answered by shorter backing phrase',
 'question-answer hook: chorus opens with a question and resolves with an unexpected answer',
 'contrast phrasing: long cinematic verse lines then short punchy chorus lines',
 'prosody stress check: natural Vietnamese spoken stresses must land on strong beats',
 'active verbs only: avoid static abstract nouns, make images move',
 'metaphor collision: combine two unrelated concrete domains into one central image',
 'sensory ladder: verse moves from sight to sound to touch to inner feeling',
 'time jump: verse 1 before, verse 2 after, bridge reveals the cost',
 'single room drama: entire lyric occurs in one location with escalating details',
 'recolor title: verse 2 changes what the title means',
 'negative space: leave one short line alone before chorus for impact',
 'internal rhyme weave: one internal rhyme per two lines, no forced end rhyme',
 'slant rhyme texture: near rhymes and vowel echoes instead of nursery perfect rhymes',
 'motif mutation: repeat one tiny image but alter its verb each section',
 'vocal gesture hook: include singable vowels/ooh/ơi/hơ only if genre-appropriate',
 'bridge reversal: bridge contradicts the chorus then final chorus absorbs it',
 'micro-story arc: desire → obstacle → decision → consequence',
 'cinematic cut: each verse line is a camera shot, not an explanation',
 'folk proverb inversion: use Vietnamese proverb rhythm but twist the meaning',
 'childlike simplicity: concrete playful nouns, short verbs, easy echo hook',
 'bolero nostalgia: place/time/weather/object but avoid generic rain-and-memory unless seed demands it',
 'cai-luong dialogue: spoken-sung conflict line before vọng cổ lift',
 'epic chant architecture: sparse mythic nouns, rising imperatives, choir-friendly vowels',
 'jazz instrumental prompt: no lyric story, instead describe melodic arc and solo handoffs',
]

STRUCTURE_TEMPLATES = [
 'Intro -> Verse 1 -> Pre-Chorus -> Chorus -> Verse 2 -> Pre-Chorus -> Chorus -> Bridge -> Final Chorus -> Outro',
 'Chorus (cold open) -> Verse 1 -> Chorus -> Verse 2 -> Bridge -> Final Chorus -> Outro',
 'Intro -> Verse 1 -> Pre-Chorus -> Chorus -> Verse 2 -> Bridge -> Final Chorus -> Outro',
 'Intro -> Verse 1 -> Pre-Chorus -> Chorus -> Post-Chorus -> Verse 2 -> Chorus -> Post-Chorus -> Bridge -> Final Chorus + Post-Chorus',
 'Intro (instruments) -> Verse 1 -> Spoken-Sung Dialogue -> Pre-Chorus -> Chorus -> Verse 2 -> Bridge -> Final Chorus',
 'Intro -> Verse 1 -> Hook -> Verse 2 -> Bridge -> Hook -> Outro',
]

HOOK_TECHNIQUE_BANK = [
 'title on downbeat, then consequence line',
 'two-word hook repeated with different emotional color',
 'ascending three-line hook: small → larger → release',
 'echo hook: lead phrase plus bracketed backing answer',
 'imperative hook: one command listeners can chant',
 'confession hook: plain sentence that hurts because it is true',
 'image hook: chorus built around one striking visual object',
 'contrast hook: soft first half, explosive second half',
 'list hook: three concrete images ending in title',
 'anti-hook: intentionally quiet line after dense verse',
 'post-chorus vowel tag: simple Vietnamese vowel phrase for memorability',
 'final-word hook: every chorus line lands on same emotional keyword family',
]

SECTION_ENERGY_BANK = [
 'Verse = intimate detail, Pre = tension question, Chorus = simple release, Bridge = reversal',
 'Verse = narrative, Chorus = slogan, Verse2 = consequence, Bridge = secret',
 'Cold hook first, then explain with verse, final chorus changes one key line',
 'No pre-chorus: verse drops directly into hook for urgency',
 'Two short verses, long chorus, bridge as whispered confession',
 'Sparse verse with long vowels, chorus with clipped rhythmic phrases',
]


VOCAL_PALETTES = {
 'Rap': ['male baritone rapper with gritty chest tone', 'female alto rapper with sharp staccato diction', 'male-female tradeoff rap duet', 'spoken-word male lead with sung female hook'],
 'Rock': ['raspy male tenor rock lead', 'powerful female alto rock lead', 'male-female gang vocal duet', 'raw male lead with female harmony lift'],
 'Pop': ['breathy female lead', 'smooth male tenor lead', 'male-female romantic duet', 'androgynous airy lead with stacked choir'],
 'Ballad': ['intimate female mezzo-soprano', 'warm male tenor', 'male-female call-and-response duet', 'fragile female lead with male low harmony'],
 'EDM': ['ethereal female topline', 'smooth male topline', 'chopped androgynous vocal hook', 'female lead with male vocoder response'],
 'Lofi': ['soft sleepy female vocal', 'mellow male bedroom vocal', 'whispered duet', 'hummed backing with intimate lead'],
 'Thien': ['serene female mantra lead', 'calm male chant lead', 'mixed temple choir response', 'soft female lead with low male drone'],
 'Phat-Phap': ['calm male chant lead', 'gentle female devotional lead', 'mixed choir antiphonal response', 'elder male recitation with female chorus'],
 'Cinematic': ['heroic female lead and huge choir', 'male chant lead with female ad-libs', 'mixed epic choir', 'solo soprano rising into choir'],
 'Remix-Cover': ['silky female club vocal', 'smooth male nu-disco vocal', 'duet hook with chopped vocal doubles', 'androgynous processed club lead'],
 'Experimental': ['surreal spoken-sung female lead', 'low male narrator with alien choir', 'androgynous glitch vocal', 'fragmented duet through granular effects'],
 'Opera': ['dramatic soprano lead', 'heroic tenor lead', 'mezzo-soprano with baritone response', 'soprano-tenor duet with mixed choir'],
 'Cai-Luong': ['female cải lương lead with ornamented vibrato', 'male vọng cổ lead with dramatic bends', 'male-female cải lương dialogue duet', 'ensemble theatre chorus response'],
 'Bolero': ['warm male bolero crooner', 'sweet female bolero lead', 'male-female nostalgic duet', 'soft group backing harmony'],
 'Thieu-Nhi': ['bright child lead vocal', 'children choir unison', 'boy-girl kid duet', 'playful adult narrator with children response'],
 'Restaurant-Jazz-Instrument': ['solo piano lead', 'warm tenor sax lead', 'hollow-body jazz guitar lead', 'piano trio lead with sax replies'],
 'Cinematic-MaxMax': ['massive mixed choir lead', 'heroic soprano ad-lib lead', 'low male warrior chant lead', 'orchestral brass and choir lead'],
 'Other': ['joyful unisex lead', 'female folk lead', 'male world-fusion lead', 'communal group vocal'],
 'Instrumental': ['solo piano lead', 'bamboo flute lead', 'cello lead', 'cinematic string ensemble lead'],
 'Relax-Sleep': ['warm pad lead', 'singing bowl lead', 'ocean drone lead', 'forest night texture lead'],
}

PRODUCTION_MICRO = [
 'microtiming: humanized groove with intentional push-pull, not quantized-flat',
 'drum design: transient-shaped kick, layered snare tail, tasteful ghost notes',
 'bass movement: melodic counter-motion instead of static root notes',
 'harmony design: suspended chords resolving late, modal color notes, non-obvious cadence',
 'stereo field: dry intimate center vocal/instrument, wide chorus pads, automated depth',
 'transition FX: reverse swells, filtered pre-lift, one signature ear-candy per section',
 'master target: loud but breathable, clean low-end separation, no smeared reverb',
 'anti-cliche: avoid stock chord loop, avoid generic four-bar repetition, vary section density',
]

def vocal_choice(genre, iteration):
    palette = VOCAL_PALETTES.get(genre, VOCAL_PALETTES['Other'])
    # Hard cycle by generation index so consecutive generations change singer identity.
    return palette[iteration % len(palette)]

def production_chain(title, iteration):
    # 4 different micro-hints per song, deterministic but varied
    vals=[]
    for i in range(4): vals.append(pick(f'{title}|prod|{iteration}|{i}', PRODUCTION_MICRO))
    return '; '.join(dict.fromkeys(vals))

NEGATIVE = {
 'default':'generic stock loop, karaoke backing track, muddy mix, weak hook, repetitive lyrics, same imagery, flat arrangement',
 'Instrumental':'singing, rap, spoken word, choir, vocal hook, sharp transients',
 'Relax-Sleep':'lead vocal, hard drums, snare, sudden drop, harsh highs, aggressive bass, busy melody',
}

def used_titles():
    vals=[]
    for p in LIB.glob('*/*/metadata.json'):
        try:
            m=json.loads(p.read_text())
            vals.append(m.get('title',''))
            vals.extend(' '.join(t.get('title','').split('#')[:1]).strip() for t in m.get('takes',[]))
        except Exception: pass
    return set(x for x in vals if x)

def pick(seed, arr):
    return arr[int(hashlib.sha1(seed.encode()).hexdigest(),16) % len(arr)]

def compact_style(text: str, limit: int = 950) -> str:
    """Keep under Suno v5.5 style limit while preserving highest-signal clauses."""
    if len(text) <= limit:
        return text
    clauses = [c.strip() for c in text.split(';') if c.strip()]
    priority = []
    keys = ['genre DNA', 'singer identity', 'vocal register', 'rhythm section', 'signature concept', 'hook design', 'arrangement map', 'mix/master target', 'strictly avoid']
    for key in keys:
        for c in clauses:
            if key.lower() in c.lower() and c not in priority:
                priority.append(c)
                break
    # Add remaining short production clauses until limit.
    for c in clauses:
        if c not in priority and len(c) < 130:
            priority.append(c)
    out = '; '.join(priority)
    if len(out) > limit:
        out = out[:limit-1].rsplit(';', 1)[0]
    return out

def build_style(genre, base_title, seed_pack, iteration):
    dna=GENRE_DNA.get(genre, GENRE_DNA['Other'])
    hook=pick(base_title+str(iteration)+'hook', HOOK_SHAPES)
    arrangement=pick(base_title+str(iteration)+'arr', ARRANGEMENTS)
    vocalist=vocal_choice(genre, iteration)
    prod=production_chain(base_title, iteration)
    style = (f"Hyper-realistic commercial Suno v5.5 master; leading genre DNA: {genre}, {dna['bpm']}, {dna['groove']}; "
             f"singer identity: {vocalist}; vocal register/performance: {dna['vocal']}; "
             f"rhythm section: {dna['prod']}; advanced production chain: {prod}; "
             f"signature concept motif: {seed_pack[1]} ({seed_pack[2]}); hook design: {hook}; "
             f"arrangement map: {arrangement}; mix/master target: separated low-end, clear transients, intentional stereo depth, dynamic contrast, premium non-generic finish; "
             f"strictly avoid pop-washing, stock loops, reused melodic contour, recycled lyric imagery")
    return compact_style(style)

def last_generated_lyrics(genre: str) -> str:
    files = sorted((LIB / '_batch-lyrics').glob(f'{genre}_*.txt'), key=lambda x: x.stat().st_mtime, reverse=True)
    for f in files:
        try:
            txt = f.read_text(encoding='utf-8').strip()
            if txt:
                return txt[:2500]
        except Exception:
            pass
    return ''

def lyric_similarity(a: str, b: str) -> float:
    def toks(x): return set(re.findall(r"[\wÀ-ỹ]+", x.lower()))
    A, B = toks(a), toks(b)
    return len(A & B) / max(1, len(A | B)) if A and B else 0.0

def llm_generate_lyrics(genre, title, seed_pack, iteration, vocalist, hook_shape, rhyme_texture):
    prev = last_generated_lyrics(genre)
    idea_en, idea_vi, axis = seed_pack
    craft = pick(f'{genre}|{title}|{iteration}|craft', LYRIC_CRAFT_TECHNIQUES)
    hook_tip = pick(f'{genre}|{title}|{iteration}|hooktip', HOOK_TECHNIQUE_BANK)
    energy_map = pick(f'{genre}|{title}|{iteration}|energy', SECTION_ENERGY_BANK)
    structure = pick(f'{genre}|{title}|{iteration}|struct', STRUCTURE_TEMPLATES)
    prompt = f"""Viết lyrics tiếng Việt hoàn toàn mới cho Suno.

RÀNG BUỘC CỨNG:
- Không dùng template cũ, không dùng câu sáo rỗng.
- Không lặp bất kỳ câu/ý/hook nào với BÀI LIỀN TRƯỚC bên dưới.
- Khác chủ đề rõ ràng với bài liền trước.
- Giữ section labels Suno bằng tiếng Anh trong ngoặc vuông.
- Lyrics thuần Việt, không markdown ngoài section labels.
- 180-260 từ, đủ cấu trúc bài hát.
- Title: {title}
- Genre: {genre}
- Concept seed: {idea_vi} / {axis}
- Vocalist: {vocalist}
- Hook shape: {hook_shape}
- Rhyme texture: {rhyme_texture}
- Kỹ thuật lyric bắt buộc dùng: {craft}
- Hook tip bắt buộc dùng: {hook_tip}
- Energy/section map: {energy_map}
- Cấu trúc section bắt buộc (dùng section labels tiếng Anh trong [] cho từng phần): {structure}
- BẮT BUỘC: mỗi phần mở đầu bằng một dòng [Section] (vd [Intro], [Verse 1], [Chorus], [Bridge], [Outro]); tối thiểu 5 section; phải có Intro, Chorus, và một hook rõ ràng ([Hook] hoặc Chorus đóng vai hook).
- BẮT BUỘC có một hook bắt tai (random loại: vocal hook/earworm, instrumental hook, chant, post-chorus tag, call-response, title-drop — chọn hợp thể loại).
- CHỈ trả lyrics thuần + section labels trong lyrics; KHÔNG kèm ```; KHÔNG kèm field style trong lyrics.

BÀI LIỀN TRƯỚC ĐỂ TRÁNH NA NÁ:
<<<
{prev if prev else '(chưa có)'}
>>>

Trả về JSON duy nhất dạng:
{{"lyrics":"..."}}
"""
    models = [os.environ.get('SUNO_LYRIC_MODEL','gptplus4/cx/gpt-5.5'), 'router9/cc/claude-sonnet-4-6', 'openai/gpt-5.4-mini', 'venice/openai-gpt-4o-mini-2024-07-18']
    # F-08: keep total LLM time under the batch-runner's 240s seed budget.
    # Global deadline 210s; each model gets min(90s, remaining) so we never get SIGKILLed mid-chain.
    import time as _time
    _deadline = _time.monotonic() + 210
    for model in models:
        _remaining = _deadline - _time.monotonic()
        if _remaining < 10:
            break
        try:
            proc = subprocess.run(['openclaw','infer','model','run','--gateway','--model',model,'--prompt',prompt,'--json'], cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=min(90, _remaining))
            raw = proc.stdout.strip()
            if proc.returncode != 0 or not raw:
                continue
            m = re.search(r'\{.*\}', raw, re.S)
            if not m:
                continue
            obj = json.loads(m.group(0))
            text = obj.get('lyrics') or obj.get('text') or obj.get('content') or ''
            if not text and isinstance(obj.get('outputs'), list) and obj['outputs']:
                text = obj['outputs'][0].get('text', '')
            if isinstance(text, dict): text = text.get('lyrics','')
            text = str(text).strip()
            # Strip markdown code fences the model may wrap around JSON/lyrics.
            fence = re.match(r'^```[a-zA-Z]*\s*(.*?)\s*```$', text, re.S)
            if fence:
                text = fence.group(1).strip()
            # Provider wrappers often return text that itself is JSON.
            if text.startswith('{'):
                try:
                    inner = json.loads(text)
                    text = inner.get('lyrics') or inner.get('text') or text
                    if isinstance(text, dict): text = text.get('lyrics','')
                    text = str(text).strip()
                except Exception:
                    pass
            if text and len(text) > 350 and lyric_similarity(text, prev) < 0.22:
                return text
        except Exception:
            continue
    return None

def build_lyrics(genre, title, seed_pack, iteration):
    idea_en, idea_vi, axis = seed_pack
    texture = pick(title+str(iteration)+'rhyme', RHYME_TEXTURES)
    hook = pick(title+str(iteration)+'hook', HOOK_SHAPES)
    vocalist = vocal_choice(genre, iteration)
    if genre in ('Instrumental','Relax-Sleep','Restaurant-Jazz-Instrument'):
        return f"[Instrumental Intro - {idea_vi}, signature motif]\n\n[Instrumental Section A - establish texture, slow motion]\n\n[Instrumental Section B - add counter-melody, wider stereo]\n\n[Instrumental Bridge - strip to one motif, deep space]\n\n[Instrumental Final Section - emotional lift without vocals]\n\n[Instrumental Outro - clean slow fade]"
    llm = llm_generate_lyrics(genre, title, seed_pack, iteration, vocalist, hook, texture)
    if llm:
        return llm
    return f"[Intro - scene setting]\n{idea_vi.capitalize()}\n\n[Verse 1]\nHôm nay câu chuyện bắt đầu từ một vật rất riêng\nNó đổi màu theo nhịp thở của {genre}\nTa không mượn đường cũ để đi qua bài hát\nChỉ giữ một dấu hiệu nhỏ: {axis}\n\n[Chorus]\n{title}\nTên ấy mở một hướng khác\n{title}\nMỗi nhịp rẽ sang một miền chưa quen\n\n[Verse 2]\nKhông kể lại bóng cũ, không vay lại lời xưa\nNhân vật trong bài tự tìm lấy giọng mình\nMột chi tiết lạ kéo không gian chuyển động\nVà đoạn cuối khép bằng một hình ảnh mới\n\n[Outro]\n{title}\nTắt dần, nhưng không giống bài nào trước đó"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--genre', required=True); ap.add_argument('--title', required=True)
    ap.add_argument('--iteration', type=int, default=0)
    ap.add_argument('--base-json')
    args=ap.parse_args()
    seed=f"{args.genre}|{args.title}|{args.iteration}|{len(used_titles())}"
    seed_pack=pick(seed, IDEA_BANK)
    title=args.title
    existing=used_titles()
    if title in existing:
        # Ensure repeated generated variants get a distinct conceptual title.
        title = f"{title} - {seed_pack[0].title()}"
    out={
        'title': title,
        'genre': args.genre,
        'idea_seed': {'key':seed_pack[0], 'image_vi':seed_pack[1], 'axis':seed_pack[2]},
        'vocalist': vocal_choice(args.genre, args.iteration),
        'style_prompt': build_style(args.genre, title, seed_pack, args.iteration),
        'lyrics': build_lyrics(args.genre, title, seed_pack, args.iteration),
        'exclude': NEGATIVE.get(args.genre, NEGATIVE['default']),
        'weirdness': 66 if args.genre not in ('Ballad','Relax-Sleep','Instrumental') else 45,
        'style_influence': 90,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
if __name__=='__main__': main()
