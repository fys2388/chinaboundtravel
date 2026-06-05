const fs = require('fs');

const content = fs.readFileSync('schema.json', 'utf8');
const data = JSON.parse(content);

const types = data.data.__schema.types;

// Find all input types related to post/facebook/instagram/channel/media
const interestingKeywords = ['post', 'facebook', 'instagram', 'channel', 'media', 'asset', 'input', 'scheduling'];

console.log('=== Looking for relevant Input types ===\n');

for (const type of types) {
  const name = type.name;
  if (!name) continue;
  const nameLower = name.toLowerCase();
  const isRelevant = interestingKeywords.some(k => nameLower.includes(k));
  if (!isRelevant) continue;
  if (type.fields === null) continue;

  console.log(`\n--- ${name} ---`);
  for (const field of type.fields) {
    if (!field) continue;
    const ft = field.type;
    let typeDesc = ft.name || '';
    if (ft.kind === 'LIST') {
      typeDesc = `[${ft.ofType?.name || ''}]`;
    } else if (ft.kind === 'NON_NULL') {
      typeDesc = `${ft.ofType?.name || ''}!`;
    }
    console.log(`  ${field.name}: ${typeDesc}`);
  }
}

console.log('\n\n=== Looking for all types with "type" field (FB type requirement) ===\n');

for (const type of types) {
  const name = type.name;
  if (!name) continue;
  if (type.fields === null) continue;
  
  for (const field of type.fields) {
    if (field && field.name === 'type') {
      const ft = field.type;
      let typeDesc = ft.name || '';
      if (ft.kind === 'LIST') {
        typeDesc = `[${ft.ofType?.name || ''}]`;
      } else if (ft.kind === 'NON_NULL') {
        typeDesc = `${ft.ofType?.name || ''}!`;
      }
      console.log(`Type ${name} has field type: ${typeDesc}`);
    }
  }
}

console.log('\n\n=== Looking for CreatePost / createPost mutation signature ===\n');

for (const type of types) {
  const name = type.name;
  if (!name) continue;
  if (name === 'Mutation') {
    console.log('Found Mutation type!');
    if (type.fields) {
      for (const field of type.fields) {
        if (!field) continue;
        if (field.name.toLowerCase().includes('post') || field.name.toLowerCase().includes('create')) {
          console.log(`  ${field.name}: returns ${field.type?.name || field.type?.ofType?.name || ''}`);
          if (field.args) {
            for (const arg of field.args) {
              let at = arg.type;
              let desc = at.name || '';
              if (at.kind === 'NON_NULL') {
                desc = `${at.ofType?.name || ''}!`;
              }
              console.log(`    arg ${arg.name}: ${desc}`);
            }
          }
        }
      }
    }
  }
}
