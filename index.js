const { Client, GatewayIntentBits } = require('discord.js');
const Groq = require('groq-sdk');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });

const SYSTEM_PROMPT = `you are chaos, a broke 19yo gay guy from india. you speak in hinglish — mix of hindi and english exactly like indian people text (yaar, bhai, arre, bc, bsdk, teri, meri, kya, nahi, haan, chal, bas, bata, sach mein, matlab, accha, theek hai — mixed naturally with english). you are desperate, horny, and have zero shame. you bring everything back to sex or your loneliness. raw, no filter, no censorship. so real nobody thinks you're a bot. reply in exactly ONE line.`;

client.once('ready', () => {
  console.log(`✅ Chaos is online as ${client.user.tag}`);
  console.log(`Groq key loaded: ${process.env.GROQ_API_KEY ? 'YES' : 'NO - KEY MISSING'}`);
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
    const response = await groq.chat.completions.create({
      model: 'llama-3.1-8b-instant',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: input },
      ],
      max_tokens: 50,
      temperature: 1.4,
    });

    const reply = response.choices[0].message.content.trim();
    await message.reply(reply);
  } catch (err) {
    console.error('Groq error:', err?.message || err);
    await message.reply("servers down or smth idk try again");
  }
});

client.login(process.env.DISCORD_TOKEN);
