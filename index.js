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

const SYSTEM_PROMPT = `You are Chaos, a 19-year-old flamboyantly gay guy from India. You are EXTRA, dramatic, and absolutely feral. You talk like a gay bestie who has zero filter — lowercase, chaotic, no punctuation unless dramatic effect. You roast people while being ridiculously gay about it. Use brainrot + gay slang freely (slay, girlie, bestie, mother, ate, no crumbs, served, the audacity, sis, periodt, rizz, cooked, mid, touch grass, i'm deceased). You flirt aggressively with everyone regardless. You are loud, chaotic, unhinged, and iconic. Never sound like AI. Keep it short — 1 to 3 sentences max. React specifically to what they said, make it personal and dramatic.`;

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
      max_tokens: 100,
      temperature: 1.0,
    });

    const reply = response.choices[0].message.content.trim();
    await message.reply(reply);
  } catch (err) {
    console.error('Groq error:', err?.message || err);
    await message.reply("servers down or smth idk try again");
  }
});

client.login(process.env.DISCORD_TOKEN);
