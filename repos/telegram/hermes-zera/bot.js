require("dotenv").config();
const fs = require("fs");
const TelegramBot = require("node-telegram-bot-api");
const Anthropic = require("@anthropic-ai/sdk");

const soulMd = fs.readFileSync("./SOUL.md", "utf-8");
const bot = new TelegramBot(process.env.TELEGRAM_BOT_TOKEN, { polling: true });
const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const conversations = new Map();

bot.on("message", async (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;

  if (!text || text.startsWith("/start")) {
    bot.sendMessage(
      chatId,
      `🌌 Привет! Я ${process.env.AGENT_NAME || "Hermes Zera"}. Чем могу помочь?`
    );
    return;
  }

  // Keep conversation history per chat
  if (!conversations.has(chatId)) conversations.set(chatId, []);
  const history = conversations.get(chatId);
  history.push({ role: "user", content: text });

  // Keep last 20 messages to stay within context
  if (history.length > 20) history.splice(0, history.length - 20);

  try {
    const response = await anthropic.messages.create({
      model: process.env.MODEL || "claude-sonnet-4-20250514",
      max_tokens: 1024,
      system: soulMd,
      messages: history,
    });

    const reply = response.content[0].text;
    history.push({ role: "assistant", content: reply });
    bot.sendMessage(chatId, reply, { parse_mode: "Markdown" });
  } catch (err) {
    console.error("Error:", err.message);
    bot.sendMessage(chatId, "Извини, что-то пошло не так. Попробуй ещё раз.");
  }
});

console.log(`🌌 ${process.env.AGENT_NAME || "Hermes Zera"} запущен в Telegram...`);
