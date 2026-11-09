"""Attribute pools and prompt rendering.

All vocabularies are local constants, so prompt generation is free, offline and
does not depend on any paid service. The pools are deliberately large: combined
they produce millions of distinct photo blueprints.
"""

from __future__ import annotations

CATEGORY_LABELS = {
    "girls": "Girls",
    "boys": "Boys",
    "lifestyle": "Lifestyle",
    "fashion": "Fashion",
    "travel": "Travel",
    "food": "Food",
    "nature": "Nature",
    "fitness": "Fitness",
    "street": "Street",
    "architecture": "Architecture",
}

CATEGORIES = list(CATEGORY_LABELS)

PERSON_CATEGORIES = ("girls", "boys", "fashion", "fitness", "street")
MIXED_CATEGORIES = ("lifestyle", "travel")
SCENE_CATEGORIES = ("food", "nature", "architecture")

# Probability that a "mixed" category renders a person instead of a pure scene.
MIX_PROBABILITY = {"lifestyle": 0.65, "travel": 0.55}

NEGATIVE_PROMPT = (
    "text, letters, watermark, logo, signature, caption overlay, deformed hands, "
    "extra fingers, extra limbs, fused fingers, distorted face, crossed eyes, "
    "bad anatomy, plastic skin, waxy skin, blurry, low resolution, jpeg artifacts, "
    "cartoon, anime, illustration, 3d render, duplicate subject, cropped head, "
    "oversaturated, airbrushed, uncanny"
)

# ---------------------------------------------------------------------------
# Person attributes
# ---------------------------------------------------------------------------

HERITAGES = [
    "South Asian",
    "East Asian",
    "Southeast Asian",
    "Black African",
    "Afro-Caribbean",
    "Middle Eastern",
    "North African",
    "Latina",
    "Mediterranean",
    "Nordic",
    "Slavic",
    "mixed-race",
    "Pacific Islander",
    "Indigenous American",
    "Irish",
    "Ethiopian",
    "Filipino",
    "Japanese",
    "Korean",
    "Brazilian",
    "Nigerian",
    "Indian",
    "Turkish",
    "Moroccan",
    "Vietnamese",
    "Ghanaian",
    "Mexican",
    "Persian",
    "Italian",
    "Kenyan",
]

AGES = {
    "woman": [
        "in her early 20s",
        "in her mid 20s",
        "in her late 20s",
        "in her early 30s",
        "in her mid 30s",
        "in her late 30s",
        "in her early 40s",
        "in her late 40s",
    ],
    "man": [
        "in his early 20s",
        "in his mid 20s",
        "in his late 20s",
        "in his early 30s",
        "in his mid 30s",
        "in his late 30s",
        "in his early 40s",
        "in his late 40s",
    ],
}

HAIR_STYLES = [
    "long straight hair",
    "shoulder-length wavy hair",
    "tight curly hair",
    "short cropped hair",
    "a high bun",
    "a messy ponytail",
    "braided hair",
    "a pixie cut",
    "slicked-back hair",
    "loose curls",
    "a layered wolf cut",
    "a blunt bob",
    "a buzz cut",
    "an undercut fade",
    "a side-part quiff",
    "a textured fringe",
    "space buns",
    "a braided crown",
    "a low chignon",
    "shoulder-length locs",
]

HAIR_COLORS = [
    "jet black",
    "dark brown",
    "chestnut brown",
    "honey blonde",
    "platinum blonde",
    "auburn",
    "copper red",
    "ash brown",
    "silver-grey",
    "blue-black",
    "caramel highlights",
    "sun-bleached brown",
]

EYES = [
    "dark brown eyes",
    "warm hazel eyes",
    "deep green eyes",
    "steel blue eyes",
    "amber eyes",
    "soft grey eyes",
    "almond-shaped dark eyes",
    "wide brown eyes",
]

FACES = [
    "high cheekbones",
    "a strong angular jawline",
    "a round face with full cheeks",
    "an oval face with delicate features",
    "a square jaw",
    "a heart-shaped face",
    "a strong brow",
    "freckled cheeks",
    "a dimpled smile",
    "a beauty mark near the lip",
    "a straight nose and defined lips",
    "soft rounded features",
    "a sharp profile",
    "a wide friendly smile",
]

BUILDS = [
    "a slim build",
    "an athletic build",
    "a curvy figure",
    "a tall lean frame",
    "a petite frame",
    "broad shoulders",
    "a stocky build",
    "modelesque proportions",
]

EXPRESSIONS = [
    "a relaxed half-smile",
    "a genuine laugh",
    "a calm serious gaze",
    "a soft confident smile",
    "a playful grin",
    "a thoughtful distant look",
    "a gentle closed-mouth smile",
    "a bold direct stare",
    "a warm open smile",
    "a subtle smirk",
    "a surprised bright expression",
    "a serene relaxed expression",
]

ACCESSORIES = [
    "thin gold hoop earrings",
    "a minimalist silver watch",
    "oversized sunglasses",
    "a leather crossbody bag",
    "layered beaded necklaces",
    "a wide-brim sun hat",
    "a baseball cap",
    "a silk scarf",
    "a chunky ring set",
    "wire-rim glasses",
    "a knitted beanie",
    "a bucket hat",
    "a structured tote bag",
    "a delicate pendant necklace",
    "a stack of bracelets",
    "no accessories",
]

OUTFITS = {
    "girls": [
        "a flowy pastel sundress",
        "an oversized knit sweater with denim shorts",
        "a fitted ribbed tank and wide-leg trousers",
        "a floral midi dress with white sneakers",
        "a linen button-down and cream shorts",
        "a cropped denim jacket over a white tee",
        "a silk slip dress with a soft cardigan",
        "a sporty crop top and joggers",
        "a tailored blazer dress",
        "a cozy loungewear set",
        "a checked shirt tied at the waist",
        "a pleated tennis skirt and polo shirt",
        "a ribbed bodycon dress with ankle boots",
        "a pinafore dress over a striped long-sleeve",
    ],
    "boys": [
        "a relaxed linen shirt and chinos",
        "a plain white tee with black jeans",
        "an oversized hoodie and cargo pants",
        "a tailored navy suit with no tie",
        "a denim jacket over a grey tee",
        "a merino polo and pleated trousers",
        "a bomber jacket and slim jeans",
        "a knitted sweater over a collared shirt",
        "a graphic tee and varsity jacket",
        "a camp-collar shirt and tailored shorts",
        "a black turtleneck and wool coat",
        "a track jacket with retro sneakers",
        "a corduroy overshirt and straight jeans",
        "a crisp oxford shirt with rolled sleeves",
    ],
    "fashion": [
        "an avant-garde structured coat with bold shoulders",
        "a monochrome tailored suit",
        "a metallic slip dress with statement heels",
        "a deconstructed denim look with layered belts",
        "a floor-length pleated gown",
        "a leather trench over a knit dress",
        "a colour-blocked designer-inspired set",
        "a sharp pinstripe suit with a silk shirt",
        "a dramatic ruffled blouse with wide trousers",
        "a futuristic techwear outfit with utility straps",
        "a sculptural off-shoulder top and column skirt",
        "a sequined jacket over a plain tank",
    ],
    "fitness": [
        "a matching seamless activewear set",
        "a performance tank and running shorts",
        "a zip-up track jacket and leggings",
        "a compression top and joggers",
        "a sports bra and high-waist leggings with a windbreaker",
        "a breathable training tee and shorts",
        "a fitted long-sleeve running top and tights",
        "a hooded sweatshirt with tapered joggers",
    ],
    "street": [
        "an oversized graphic hoodie and baggy jeans",
        "a varsity jacket with cargo pants",
        "a bucket hat with a boxy tee and wide shorts",
        "a puffer jacket over a hoodie",
        "a flannel shirt and distressed jeans",
        "a tracksuit with chunky sneakers",
        "a cropped bomber jacket and parachute pants",
        "a jersey with layered chains and wide-leg denim",
    ],
    "lifestyle": [
        "a soft cotton overshirt with relaxed trousers",
        "a chunky knit cardigan and jeans",
        "a plain tee with linen pants",
        "a cozy fleece and leggings",
        "a simple midi dress with a denim jacket",
        "a henley shirt and chinos",
        "a matching loungewear set",
        "a light sweater over a collared shirt",
    ],
    "travel": [
        "a breathable linen shirt and loose trousers",
        "a sundress with a woven straw bag",
        "a lightweight utility jacket and hiking trousers",
        "a striped tee with rolled chinos",
        "a long flowing skirt and fitted top",
        "a chambray shirt and walking shorts",
        "a quilted vest over a knit sweater",
        "a loose kaftan with sandals",
    ],
}

POSES = [
    "standing with weight on one hip",
    "walking mid-stride toward the camera",
    "leaning against a wall with arms crossed",
    "sitting on a low step with hands on knees",
    "looking back over one shoulder",
    "adjusting hair with one hand",
    "hands in pockets with relaxed shoulders",
    "laughing with head tilted back",
    "sitting at a cafe table holding a coffee cup",
    "mid-twirl with fabric in motion",
    "crouching slightly with elbows on knees",
    "stretching before a run",
    "holding a camera up to one eye",
    "resting chin on one hand at a window",
    "striding across a crosswalk",
    "jumping playfully with arms outstretched",
    "standing in profile gazing into the distance",
    "walking away from the camera while glancing back",
    "leaning on a railing looking down",
    "holding a bouquet close to the chest",
    "sitting on a wall with legs dangling",
    "reading a book with knees pulled up",
]

BACKGROUNDS = {
    "girls": [
        "a sunlit cafe terrace with hanging plants",
        "a pastel-painted street corner",
        "a rooftop with a soft city skyline",
        "a quiet garden path with blooming flowers",
        "a minimalist studio with a warm backdrop",
        "a bookstore aisle with tall shelves",
        "a beach boardwalk at golden hour",
        "a modern apartment with large windows",
        "a flower market bursting with colour",
        "a tree-lined boulevard with dappled shade",
        "a vintage record shop",
        "a bright bakery counter",
    ],
    "boys": [
        "a concrete parking structure with clean lines",
        "a downtown street with brick facades",
        "a barbershop interior with mirrors",
        "a riverside promenade",
        "a rooftop basketball court",
        "a modern office lobby",
        "a garage workshop with tools",
        "a subway platform with tiled walls",
        "a desert highway pull-off",
        "a coffee shop window seat",
        "a record store with crates of vinyl",
        "a skate park at dusk",
    ],
    "fashion": [
        "a stark white studio with a single spotlight",
        "a backstage runway corridor",
        "a marble staircase in a grand hotel",
        "a rooftop terrace at blue hour",
        "a graffiti-covered concrete wall",
        "a mirrored elevator lobby",
        "a minimalist gallery with white walls",
        "a vintage theatre with red velvet seats",
        "a windswept beach with dramatic clouds",
        "an underground parking level with neon strips",
        "a glasshouse filled with tropical plants",
        "a city crosswalk with motion blur",
    ],
    "fitness": [
        "an industrial gym with rubber floors",
        "a running track at sunrise",
        "a rooftop yoga deck",
        "a boxing gym with hanging bags",
        "a coastal running path",
        "a climbing gym wall",
        "a park with dew-covered grass",
        "a bright functional training studio",
    ],
    "street": [
        "a neon-lit alley after rain",
        "a busy intersection with yellow taxis",
        "a graffiti wall in an industrial district",
        "a night market with string lights",
        "a basketball court with chain-link fence",
        "a stairwell with painted murals",
        "a corner store with glowing signage",
        "a skate plaza with concrete ledges",
        "a subway entrance with commuters",
        "a rooftop overlooking traffic",
    ],
    "lifestyle": [
        "a sunlit reading nook with linen curtains",
        "a cozy kitchen with fresh coffee",
        "a balcony with potted herbs",
        "a living room with a low linen sofa",
        "a garden table set for breakfast",
        "a home studio with plants and books",
        "a lakeside dock in the morning",
        "a small ceramics workshop",
        "a farmer's market stall",
        "a quiet library corner",
    ],
    "travel": [
        "a cliffside village in Santorini at golden hour",
        "a narrow Kyoto lane with wooden houses",
        "a Marrakech souk with colourful textiles",
        "a Lisbon tram climbing a steep street",
        "a Norwegian fjord viewpoint",
        "a Bali rice terrace at sunrise",
        "a Venice canal with moored gondolas",
        "a Swiss alpine meadow with wildflowers",
        "a Havana street with vintage cars",
        "a Sahara dune ridge at sunset",
        "a Scottish castle ruin on a loch",
        "a neon-lit Tokyo crosswalk at night",
        "a Peruvian mountain trail with llamas",
        "a Cape Town coastal road",
    ],
}

# ---------------------------------------------------------------------------
# Scene attributes
# ---------------------------------------------------------------------------

FOOD_DISHES = [
    "a steaming bowl of tonkotsu ramen with a soft egg",
    "a wood-fired margherita pizza with basil",
    "a stack of fluffy buttermilk pancakes with berries",
    "a colourful poke bowl with salmon and edamame",
    "a rustic sourdough loaf with cultured butter",
    "a plate of handmade tagliatelle with truffle",
    "a sizzling street-food taco trio",
    "a creamy mango sticky rice with coconut",
    "a golden butter croissant with jam",
    "a vibrant buddha bowl with roasted vegetables",
    "a rich chocolate lava cake with raspberry",
    "a fragrant bowl of Thai green curry",
    "a fresh caprese salad with heirloom tomatoes",
    "a plate of sushi nigiri arranged on slate",
]

FOOD_DETAILS = [
    "visible steam rising",
    "a glossy sauce drizzle",
    "fresh herbs scattered on top",
    "a dusting of powdered sugar",
    "melting cheese pull",
    "a sprinkle of flaky sea salt",
    "juicy textures and crisp edges",
    "a soft runny yolk",
    "caramelised char marks",
    "bright, fresh colours",
]

FOOD_SETTINGS = [
    "on a dark ceramic table",
    "on a weathered wooden board",
    "on a marble countertop",
    "on a linen tablecloth",
    "on a rustic stone surface",
    "on a slate serving board",
    "on a bright white plate",
    "on a copper tray",
]

FOOD_PROPS = [
    "with chopsticks and a linen napkin",
    "with scattered herbs and a small bowl of sauce",
    "with a vintage fork and a glass of water",
    "with a linen napkin and a sprig of rosemary",
    "with a small dish of olive oil",
    "with a cup of coffee beside it",
    "with fresh ingredients arranged around it",
    "with a folded napkin and scattered crumbs",
]

NATURE_SCENES = [
    "a misty pine forest at dawn",
    "a turquoise glacial lake beneath jagged peaks",
    "a windswept coastal cliff with crashing waves",
    "a lavender field stretching to the horizon",
    "a desert canyon with layered red rock",
    "a waterfall hidden in a mossy gorge",
    "a snow-covered birch grove",
    "a golden wheat field under dramatic clouds",
    "a volcanic black-sand beach",
    "an alpine meadow full of wildflowers",
    "a mangrove river winding through green tunnels",
    "a frozen lake with cracked ice patterns",
    "a tropical rainforest canopy with light beams",
    "a rolling green hillside with a lone tree",
]

NATURE_DETAILS = [
    "soft mist hanging in the air",
    "wildflowers in the foreground",
    "sun rays breaking through the canopy",
    "reflections on still water",
    "long shadows across the ground",
    "dew drops catching the light",
    "dramatic cloud formations",
    "textured rock and moss",
    "gentle movement in the grass",
    "layered depth fading into haze",
]

NATURE_CONDITIONS = [
    "clear skies",
    "light fog",
    "dramatic storm clouds",
    "gentle rain",
    "fresh snow",
    "hazy summer heat",
    "strong wind",
    "soft overcast light",
]

ARCHITECTURE_BUILDINGS = [
    "a brutalist concrete museum",
    "a baroque cathedral facade",
    "a glass-and-steel office tower",
    "a whitewashed Cycladic house",
    "a traditional Japanese wooden temple",
    "a modernist villa with clean lines",
    "a rusted industrial warehouse",
    "a spiral art-deco staircase",
    "a geometric library atrium",
    "a narrow European cobblestone alley",
    "a futuristic curved transport hub",
    "a red-brick Victorian terrace",
    "a desert adobe dwelling",
    "a concrete spiral parking ramp",
]

ARCHITECTURE_DETAILS = [
    "repeating windows casting strong shadows",
    "intricate stone carvings",
    "reflective glass panels",
    "exposed structural beams",
    "sweeping curved balconies",
    "weathered textures and patina",
    "symmetrical geometric patterns",
    "warm interior light glowing through glass",
    "sharp diagonal lines",
    "layered arches and colonnades",
]

ARCHITECTURE_CONDITIONS = [
    "under a clear blue sky",
    "at blue hour with interior lights on",
    "in soft morning haze",
    "after rain with wet reflections",
    "at sunset with warm light on the facade",
    "under dramatic storm clouds",
    "in crisp winter light",
    "with dappled tree shadows",
]

LIFESTYLE_SCENES = [
    "a breakfast table with coffee and fresh fruit",
    "a reading corner with an open book and blanket",
    "a home office with warm task lighting",
    "a balcony garden with watering can",
    "a linen bed with morning light",
    "a pottery studio with clay-covered hands",
    "a record player with vinyl sleeves spread out",
    "a picnic blanket under a tree",
    "a candlelit dinner setting for one",
    "a bicycle leaning against a cafe wall",
    "a basket of fresh laundry in the sun",
    "a window seat with a cup of tea",
]

LIFESTYLE_DETAILS = [
    "soft morning light across the scene",
    "a warm cup of coffee in frame",
    "an open book with a linen bookmark",
    "fresh flowers in a ceramic vase",
    "a rumpled linen throw",
    "steam rising gently",
    "everyday objects arranged naturally",
    "a calm, lived-in atmosphere",
]

TRAVEL_DETAILS = [
    "warm early light across the scene",
    "local details and worn textures",
    "a few distant travellers for scale",
    "reflections in still water",
    "colourful signage and fabrics",
    "layered architecture in the background",
    "a sense of scale and distance",
    "atmospheric haze in the distance",
]

TRAVEL_SCENES = [
    "a sunrise over a Greek island harbour",
    "a lantern-lit alley in Kyoto",
    "a camel caravan crossing Sahara dunes",
    "a train window view of the Alps",
    "a colourful market in Oaxaca",
    "a cliffside lighthouse in Portugal",
    "a longtail boat on a Thai lagoon",
    "a cobblestone plaza in Prague at dawn",
    "a glacier lagoon with floating ice",
    "a rooftop view over Istanbul at sunset",
    "a winding road through Tuscany",
    "a fishing village on the Faroe Islands",
    "a night train platform in Hanoi",
    "a hot-air balloon field in Cappadocia",
]

# ---------------------------------------------------------------------------
# Shared camera / look attributes
# ---------------------------------------------------------------------------

CAMERA_ANGLES = [
    "eye-level medium shot",
    "low-angle full-body shot",
    "high-angle overhead shot",
    "three-quarter portrait",
    "close-up on face and shoulders",
    "wide environmental shot",
    "over-the-shoulder shot",
    "dutch angle",
    "candid snapshot angle",
    "waist-up medium close-up",
    "full-body shot from a distance",
    "slightly tilted close portrait",
    "ground-level shot looking up",
    "profile side view",
]

LENSES = [
    "35mm lens",
    "50mm prime lens",
    "85mm portrait lens",
    "24mm wide-angle lens",
    "135mm telephoto lens",
    "macro detail shot",
    "anamorphic lens with soft flares",
    "tilt-shift lens",
]

LIGHTING = [
    "soft window light",
    "golden hour backlight",
    "blue hour ambient light",
    "harsh midday sun with hard shadows",
    "overcast diffused light",
    "neon signs at night",
    "warm tungsten indoor light",
    "dappled light through leaves",
    "studio softbox lighting",
    "candlelit warm glow",
    "rim light against a dark background",
    "mixed city light",
    "single hard spotlight",
    "bounced natural light from a white wall",
]

TIMES_OF_DAY = [
    "at sunrise",
    "in the early morning",
    "at midday",
    "in the late afternoon",
    "at golden hour",
    "at sunset",
    "during blue hour",
    "at night",
]

COLOR_GRADES = [
    "warm film tones",
    "a muted pastel palette",
    "a high-contrast editorial grade",
    "natural true-to-life colours",
    "a teal and orange grade",
    "a soft matte film look",
    "vibrant saturated colours",
    "desaturated cinematic tones",
    "a sun-bleached vintage palette",
    "a cool moody grade",
]

AESTHETICS = [
    "shot on 35mm film with fine grain",
    "shot on medium format film",
    "clean digital photography",
    "an analog Kodak Portra look",
    "documentary photojournalism style",
    "editorial magazine photography",
    "a candid smartphone-style photo",
    "a cinematic still frame",
    "a high-fashion campaign look",
    "a natural lifestyle photography style",
]


def article_for(word: str) -> str:
    """Best-effort indefinite article ("a South Asian woman", "an East Asian man")."""
    return "an" if word[:1].lower() in "aeiou" else "a"


def _accessory_phrase(accessories: str) -> str:
    if not accessories or accessories == "no accessories":
        return ""
    return f" with {accessories}"


def render_person_prompt(attributes: dict) -> str:
    """Compose a photorealistic person prompt from sampled attributes."""
    heritage = attributes["heritage"]
    gender = attributes["gender"]
    subject = f"{article_for(heritage)} {heritage} {gender} {attributes['age']}"
    return (
        f"Photorealistic editorial photograph of {subject}.\n"
        f"Appearance: {attributes['hair_style']} in {attributes['hair_color']}, "
        f"{attributes['eyes']}, {attributes['face']}, {attributes['build']}, "
        f"{attributes['expression']}.\n"
        f"Outfit: {attributes['outfit']}{_accessory_phrase(attributes['accessories'])}.\n"
        f"Pose: {attributes['pose']}.\n"
        f"Setting: {attributes['background']}.\n"
        f"Camera: {attributes['camera_angle']}, {attributes['lens']}.\n"
        f"Light: {attributes['lighting']}, {attributes['time_of_day']}.\n"
        f"Look: {attributes['color_grade']}, {attributes['aesthetic']}.\n"
        "Ultra-detailed, natural skin texture, realistic anatomy and proportions, "
        "sharp focus, professional photography, no text, no watermark, no logo."
    )


def render_scene_prompt(attributes: dict, category: str) -> str:
    """Compose a photorealistic scene prompt (food, nature, architecture, ...)."""
    label = CATEGORY_LABELS.get(category, category.title())
    details = ", ".join(
        part for part in (attributes.get("detail"), attributes.get("props")) if part
    )
    lines = [
        f"Photorealistic {label.lower()} photograph of {attributes['subject']}.",
    ]
    if details:
        lines.append(f"Details: {details}.")
    if attributes.get("setting"):
        lines.append(f"Setting: {attributes['setting']}.")
    lines.extend(
        [
            f"Camera: {attributes['camera_angle']}, {attributes['lens']}.",
            f"Light: {attributes['lighting']}, {attributes['time_of_day']}.",
            f"Look: {attributes['color_grade']}, {attributes['aesthetic']}.",
            "Ultra-detailed, professional photography, no text, no watermark, no logo.",
        ]
    )
    return "\n".join(lines)


def render_prompt(attributes: dict, category: str) -> str:
    if attributes.get("kind") == "person":
        return render_person_prompt(attributes)
    return render_scene_prompt(attributes, category)
