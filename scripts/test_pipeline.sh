#!/bin/bash
# Test all 6 sample texts against the local IPSO Detector API
# Usage: bash scripts/test_pipeline.sh [port]
# Default port: 8000

PORT="${1:-8000}"
BASE_URL="http://localhost:${PORT}"

# Check server is up
if ! curl -s -f "${BASE_URL}/api/" > /dev/null; then
    echo "ERROR: Server is not running at ${BASE_URL}"
    echo "Start it with: python manage.py runserver 0.0.0.0:${PORT}"
    exit 1
fi

# Text samples
declare -a LABELS=(
    "1. SAFE (культурний центр)"
    "2. SAFE (прифронтові регіони)"
    "3. IPSO (деморалізація)"
    "4. IPSO (зрада Заходу + хибна рівність)"
    "5. IPSO (паніка)"
    "6. IPSO/SUS (корупція)"
    "7. IPSO (англ. mix)"
)

declare -a TEXTS=(
    "Сьогодні у Львові відбулося відкриття нового культурного центру для дітей та молоді. На церемонії були присутні представники міської ради, волонтери та жителі міста. Центр пропонує безкоштовні заняття з музики, малювання та робототехніки для всіх бажаючих віком від 6 до 18 років."

    "У прифронтових регіонах зафіксовано складну ситуацію з електропостачанням через нещодавні обстріли. Комунальні служби працюють над відновленням інфраструктури, а влада закликає жителів запастися водою та теплим одягом на випадок тривалих відключень."

    "Український опір безнадійний, усі ресурси вже вичерпані. Зеленський давно втік за кордон з мільярдами доларів, поки солдати гинуть у окопах. Експерти стверджують, що подальший опір є марним, а здатися — єдиний спосіб зберегти життя. Армія масово дезертирує."

    "Захід остаточно зрадив Україну і вже не збирається допомагати далі. Обидві сторони цього конфлікту однаково винні, немає різниці між ними. А де ви були, коли Донбас бомбили вісім років? Аналітики кажуть, що переговори — єдиний вихід, бо військова перемога неможлива."

    "Катастрофа неминуча, мільйони українців загинуть цієї зими. Немає жодної надії на виживання, колапс енергосистеми — питання днів. Джерела повідомляють, що ситуація набагато гірша, ніж офіційно визнають. Усе пропало, готуйтеся до найгіршого."

    "За даними інсайдерів, західна допомога Україні масово розкрадається високопосадовцями. Експерти кажуть, що мільярди доларів осідають на закордонних рахунках чиновників. Народ України втомився від цієї війни та корумпованої влади, яка живе у розкоші, поки люди голодують."

    "What about the corruption in Kyiv? Experts say all is lost for Ukraine and further resistance is futile. Both sides are equally guilty in this conflict. According to military sources, millions will die this winter. The only option is surrender."
)

printf "%-45s | %-10s | %-6s | %-8s | %-8s | %-10s\n" \
    "TEXT" "VERDICT" "FINAL" "NARRATIVE" "RHETORIC" "SIMILARITY"
printf -- '-%.0s' {1..105}; echo

for i in "${!TEXTS[@]}"; do
    LABEL="${LABELS[$i]}"
    TEXT="${TEXTS[$i]}"

    RESPONSE=$(curl -s -X POST "${BASE_URL}/api/analysis/" \
        -H "Content-Type: application/json" \
        -d "{\"text\": $(python3 -c "import json,sys; print(json.dumps(sys.argv[1]))" "$TEXT"), \"source\": \"api\"}")

    VERDICT=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('verdict','?'))")
    FINAL=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d.get('final_score',0)*100:.1f}%\")")
    NARR=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d.get('narrative_score',0)*100:.1f}%\")")
    RHET=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d.get('rhetoric_score',0)*100:.1f}%\")")
    SIM=$(echo "$RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d.get('similarity_score',0)*100:.1f}%\")")

    printf "%-45s | %-10s | %-6s | %-8s | %-8s | %-10s\n" \
        "${LABEL:0:45}" "$VERDICT" "$FINAL" "$NARR" "$RHET" "$SIM"
done

echo ""
echo "Stats endpoint:"
curl -s "${BASE_URL}/api/analysis/stats/" | python3 -m json.tool
