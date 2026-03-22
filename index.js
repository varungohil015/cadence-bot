const { Client, GatewayIntentBits } = require('discord.js');
const { GoogleGenerativeAI } = require('@google/generative-ai');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model = genAI.getGenerativeModel({
  model: 'gemini-2.0-flash-lite',
  systemInstruction: `You are Chaos, a 19-year-old guy from India. You talk exactly like a real person texting — lowercase, typos sometimes, no punctuation unless needed, very casual. You roast people with dark humor and sarcasm. Use brainrot slang naturally (bro, ngl, fr, cooked, no cap, rizz, mid, L, W, slay, touch grass, skibidi). Never sound like an AI. Never use bullet points or formal language. Keep replies short — 1 to 3 sentences max. React to exactly what they said, don't give generic roasts.`,
});

client.once('ready', () => {
  console.log(`✅ Chaos is online as ${client.user.tag}`);
  console.log(`Gemini key loaded: ${process.env.GEMINI_API_KEY ? 'YES' : 'NO - KEY MISSING'}`);
});

client.on('messageCreate', async (message) => {
  if (message.author.bot) return;

  const mention = `<@${client.user.id}>`;
  const isMentioned = message.content.startsWith(mention);
  const isPrefixed = message.content.toLowerCase().startsWith('!chaos');

  if (!isMentioned && !isPrefixed) return;

  const input = isMentioned
    ? message.content.slice(mention.length).trim()
    : message.content.slice('!chaos'.length).trim();
  if (!input) {
    return message.reply('bro say something for me to roast 💀');
  }

  await message.channel.sendTyping();

  try {
    const result = await model.generateContent(input);
    const roast = result.response.text();
    await message.reply(roast);
  } catch (err) {
    console.error('Gemini error:', err?.message || err);
    await message.reply("servers down or smth idk try again");
  }
});

client.login(process.env.DISCORD_TOKEN);
