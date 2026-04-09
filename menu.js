/**
 * 今日の献立表 — Today's Menu
 *
 * Each entry in MENU_DATA represents one meal slot.
 * Fields:
 *   time  : meal time label (e.g. "朝食")
 *   name  : dish name
 *   desc  : short description
 *   kcal  : approximate calories (number)
 */
const MENU_DATA = [
  {
    time: "朝食",
    name: "ご飯・味噌汁",
    desc: "白米 + 豆腐とわかめの味噌汁",
    kcal: 320,
  },
  {
    time: "朝食",
    name: "目玉焼き",
    desc: "半熟目玉焼き・塩こしょう",
    kcal: 90,
  },
  {
    time: "昼食",
    name: "チキン南蛮",
    desc: "鶏もも肉のから揚げにタルタルソースをかけた定番料理",
    kcal: 620,
  },
  {
    time: "昼食",
    name: "野菜サラダ",
    desc: "レタス・トマト・きゅうりのシーザーサラダ",
    kcal: 110,
  },
  {
    time: "おやつ",
    name: "ヨーグルト",
    desc: "プレーンヨーグルト・はちみつがけ",
    kcal: 130,
  },
  {
    time: "夕食",
    name: "肉じゃが",
    desc: "牛肉とじゃがいも・玉ねぎの甘辛煮込み",
    kcal: 450,
  },
  {
    time: "夕食",
    name: "ほうれん草のおひたし",
    desc: "ほうれん草・醤油・かつお節",
    kcal: 45,
  },
  {
    time: "夕食",
    name: "ご飯",
    desc: "白米 180g",
    kcal: 280,
  },
];

function formatDate(date) {
  const y = date.getFullYear();
  const m = date.getMonth() + 1;
  const d = date.getDate();
  const weekdays = ["日", "月", "火", "水", "木", "金", "土"];
  const w = weekdays[date.getDay()];
  return `${y}年${m}月${d}日（${w}）`;
}

function buildTable() {
  const tbody = document.getElementById("menu-tbody");
  let totalKcal = 0;

  MENU_DATA.forEach((item) => {
    const tr = document.createElement("tr");

    const tdTime = document.createElement("td");
    tdTime.className = "meal-time";
    tdTime.textContent = item.time;

    const tdName = document.createElement("td");
    tdName.className = "meal-name";
    tdName.textContent = item.name;

    const tdDesc = document.createElement("td");
    tdDesc.className = "meal-desc";
    tdDesc.textContent = item.desc;

    const tdKcal = document.createElement("td");
    tdKcal.className = "meal-kcal";
    tdKcal.textContent = `${item.kcal} kcal`;

    tr.append(tdTime, tdName, tdDesc, tdKcal);
    tbody.appendChild(tr);
    totalKcal += item.kcal;
  });

  // Total row
  const trTotal = document.createElement("tr");
  trTotal.style.fontWeight = "bold";
  trTotal.style.background = "#fde8e4";

  const tdEmpty1 = document.createElement("td");
  const tdEmpty2 = document.createElement("td");
  const tdLabel = document.createElement("td");
  tdLabel.textContent = "合計";

  const tdTotal = document.createElement("td");
  tdTotal.className = "meal-kcal";
  tdTotal.textContent = `${totalKcal} kcal`;

  trTotal.append(tdEmpty1, tdEmpty2, tdLabel, tdTotal);
  tbody.appendChild(trTotal);
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("today-date").textContent = formatDate(new Date());
  buildTable();
});
