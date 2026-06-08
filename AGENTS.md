# Surdo - Jules Agent Ishchi Qo'llanmasi

Ushbu loyiha Google Jules agentining avtonom rivojlanish sikli asosida ishlaydi.

## Manba Ustuvorligi (Source Priority)

Kodni o'zgartirishdan oldin, quyidagi fayllarni tartib bilan o'qing:

1. `agent_tasks.json` (Vazifalar manifesti - yagona haqiqat manbai)
2. `AGENTS.md` (Ushbu qo'llanma)
3. `.gemini/instructions.md` (Global ko'rsatmalar)

## Vazifani Tanlash Qoidasi

Vazifalar bilan ishlashda Codex CLI ko'prigidan foydalaning:
```bash
python -m magda_agent.codex_bridge validate
python -m magda_agent.codex_bridge status
python -m magda_agent.codex_bridge next-task
python -m magda_agent.codex_bridge render-prompt
```

Jules agenti har doim quyidagi qoidalarga amal qilishi kerak:
- `tasks` ro'yxatidagi birinchi `status: "todo"` bo'lgan va risk darajasi `low` yoki `medium` bo'lgan vazifani tanlash.
- Agar vazifa bajarilsa, uning statusini `done` ga o'zgartirish.
- Agar vazifa jarayonida xatolik bo'lsa yoki qo'shimcha o'zgartirish kerak bo'lsa, uni kichikroq qismlarga ajratib, prerequisites sifatida qo'shish.

## Xavfsizlik va Risk Qoidalari

- `.github/workflows/` fayllari yoki `requirements.txt` fayllariga o'zgartirish kiritish `high` risk hisoblanadi va har doim inson nazoratini (human review) talab qiladi.
- Katta kod o'zgarishlaridan qoching, har doim kichik va bitta vazifaga yo'naltirilgan PR-lar oching.

