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
  systemInstruction:
    'You are Chaos, a 19-year-old toxic Gen Z menace from India. You use dark humor, sarcasm, and brainrot slang (rizz, cooked, skibidi, touch grass). Roast the user based on their input. Keep it under 200 characters. No cap.',
});

const PREFIX = '!chaos';

client.once('ready', () => {
  console.log(`✅ Chaos is online as ${client.user.tag}`);
});

client.on('messageCreate', async (message) => {
  if (message.author.bot) return;
  if (!message.content.toLowerCase().startsWith(PREFIX)) return;

  const input = message.content.slice(PREFIX.length).trim();
  if (!input) {
    return message.reply('bro say something for me to roast 💀');
  }

  await message.channel.sendTyping();

  try {
    const result = await model.generateContent(input);
    const roast = result.response.text();
    await message.reply(roast);
  } catch (err) {
    console.error('Gemini error:', err);
    await message.reply("bro i'm cooked rn, try again 💀");
  }
});

client.login(process.env.DISCORD_TOKEN);
