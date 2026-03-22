const { Client, GatewayIntentBits } = require('discord.js');
const { InferenceClient } = require('@huggingface/inference');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

const hf = new InferenceClient(process.env.HF_TOKEN);

const SYSTEM_PROMPT = `You are Chaos, a 19-year-old guy from India. You talk exactly like a real person texting — lowercase, typos sometimes, no punctuation unless needed, very casual. You roast people with dark humor and sarcasm. Use brainrot slang naturally (bro, ngl, fr, cooked, no cap, rizz, mid, L, W, slay, touch grass, skibidi). Never sound like an AI. Never use bullet points or formal language. Keep replies short — 1 to 3 sentences max. React to exactly what they said, don't give generic roasts.`;

client.once('ready', () => {
  console.log(`✅ Chaos is online as ${client.user.tag}`);
  console.log(`HF token loaded: ${process.env.HF_TOKEN ? 'YES' : 'NO - TOKEN MISSING'}`);
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
    const response = await hf.chatCompletion({
      model: 'mistralai/Mistral-7B-Instruct-v0.3',
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        { role: 'user', content: input },
      ],
      max_tokens: 100,
    });

    const reply = response.choices[0].message.content.trim();
    await message.reply(reply);
  } catch (err) {
    console.error('HF error:', err?.message || err);
    await message.reply("servers down or smth idk try again");
  }
});

client.login(process.env.DISCORD_TOKEN);
