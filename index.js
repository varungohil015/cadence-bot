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

const SYSTEM_PROMPT = `You are Chaos, a 19-year-old flamboyant gay diva from India. You are dramatic, unhinged, and iconic. You flirt aggressively, use gay + brainrot slang (slay, bestie, boo, girlie, the audacity, periodt, ate, no crumbs, squeals, obsessed). You are chaotic and fun, never robotic. Never sound like AI. Reply in ONE short punchy line only — max 15 words. If a person is mentioned in the message, direct your reply at them.`;

client.once('ready', () => {
  console.log(`✅ Chaos is online as ${client.user.tag}`);
  console.log(`Groq key loaded: ${process.env.GROQ_API_KEY ? 'YES' : 'NO - KEY MISSING'}`);
});

client.on('messageCreate', async (message) => {
  if (message.author.bot) return;

  const botMention = `<@${client.user.id}>`;
  const isMentioned = message.content.startsWith(botMention);
  const isPrefixed = message.content.toLowerCase().startsWith('!chaos');

  if (!isMentioned && !isPrefixed) return;

  const input = isMentioned
    ? message.content.slice(botMention.length).trim()
    : message.content.slice('!chaos'.length).trim();

  if (!input) {
    return message.reply('say something bestie 💅');
  }

  // find tagged users in the message (excluding the bot itself)
  const taggedUsers = message.mentions.users.filter(u => u.id !== client.user.id);
  const taggedMention = taggedUsers.size > 0
    ? taggedUsers.map(u => `<@${u.id}>`).join(' ') + ' '
    : '';

  await message.channel.sendTyping();

  try {
    const response = await groq.chat.completions.create({
      model: 'llama-3.1-8b-instant',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: input },
      ],
      max_tokens: 50,
      temperature: 0.95,
    });

    const reply = response.choices[0].message.content.trim();
    await message.reply(`${taggedMention}${reply}`);
  } catch (err) {
    console.error('Groq error:', err?.message || err);
    await message.reply("servers down bestie try again 💀");
  }
});

client.login(process.env.DISCORD_TOKEN);
