// Fetch GA4 report via Worker, save as Markdown
const fs = require('fs');
const path = require('path');

const WORKER_URL = 'https://buffer-auto-poster.fys2388.workers.dev/ga4-report';
const OUTPUT = 'e:\\AI\\dulizhan\\travel-blog\\reports\\ga4_weekly_report.md';

function fmtDuration(seconds) {
  seconds = Number(seconds) || 0;
  if (seconds >= 3600) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return h + 'h ' + m + 'm';
  }
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m + 'm ' + s + 's';
}

async function main() {
  console.log('Fetching GA4 data from Worker...');
  let resp;
  try {
    resp = await fetch(WORKER_URL);
  } catch (e) {
    console.error('Fetch error:', e.message);
    // Try without proxy
    console.log('Retrying without proxy...');
    process.env.HTTPS_PROXY = '';
    process.env.HTTP_PROXY = '';
    process.env.NO_PROXY = '*';
    resp = await fetch(WORKER_URL);
  }

  const data = await resp.json();
  console.log('Response success:', data.success);

  if (!data.success) {
    console.error('Error:', JSON.stringify(data, null, 2));
    process.exit(1);
  }

  const reports = data.reports;
  const dateRange = data.dateRange;
  const r = reports;

  // Parse daily data
  const dailyData = (r.daily && r.daily.rows || []).map(function(row) {
    const d = row.dimensionValues[0].value;
    const m = row.metricValues.map(function(v) { return v.value; });
    return {
      date: d.slice(0,4) + '-' + d.slice(4,6) + '-' + d.slice(6,8),
      users: parseInt(m[0]),
      sessions: parseInt(m[1]),
      pageviews: parseInt(m[2]),
      engaged: parseInt(m[3]),
      bounce_rate: parseFloat(m[4]) * 100,
      avg_duration: parseFloat(m[5])
    };
  });

  // Parse top pages
  const topPages = (r.topPages && r.topPages.rows || []).map(function(row) {
    const dims = row.dimensionValues.map(function(v) { return v.value; });
    const m = row.metricValues.map(function(v) { return v.value; });
    return {
      title: dims[0].slice(0, 60),
      path: dims[1],
      views: parseInt(m[0]),
      sessions: parseInt(m[1]),
      users: parseInt(m[2]),
      avg_time: parseFloat(m[3])
    };
  });

  // Parse sources
  const channelNames = {
    'Organic Search': '\u81ea\u7136\u641c\u7d22',
    'Direct': '\u76f4\u63a5\u8bbf\u95ee',
    'Social': '\u793e\u4ea4\u5a92\u4f53',
    'Referral': '\u5916\u90e8\u5f15\u8350',
    'Paid Search': '\u4ed8\u8d39\u641c\u7d22',
    'Email': '\u90ae\u4ef6\u8425\u9500',
    'Affiliates': '\u8054\u76df\u63a8\u5e7f',
    'Organic Video': '\u81ea\u7136\u89c6\u9891',
    '(Other)': '\u5176\u4ed6'
  };
  const sources = (r.sources && r.sources.rows || []).map(function(row) {
    const ch = row.dimensionValues[0].value;
    const m = row.metricValues.map(function(v) { return v.value; });
    return { channel: ch, sessions: parseInt(m[0]), users: parseInt(m[1]), engagement: parseFloat(m[2]) * 100 };
  });

  // Parse countries
  const countries = (r.countries && r.countries.rows || []).map(function(row) {
    const c = row.dimensionValues[0].value;
    const m = row.metricValues.map(function(v) { return v.value; });
    return { country: c, users: parseInt(m[0]), sessions: parseInt(m[1]), pageviews: parseInt(m[2]) };
  });

  // Parse devices
  const deviceNames = { desktop: '\u684c\u9762\u7aef', mobile: '\u79fb\u52a8\u7aef', tablet: '\u5e73\u677f' };
  const devices = (r.devices && r.devices.rows || []).map(function(row) {
    const dev = row.dimensionValues[0].value;
    const m = row.metricValues.map(function(v) { return v.value; });
    return { device: dev, sessions: parseInt(m[0]), users: parseInt(m[1]), pageviews: parseInt(m[2]) };
  });

  // Parse user type
  const userType = (r.userType && r.userType.rows || []).map(function(row) {
    const t = row.dimensionValues[0].value;
    const m = row.metricValues.map(function(v) { return v.value; });
    return { type: t, sessions: parseInt(m[0]), users: parseInt(m[1]) };
  });

  // Totals
  const totalUsers = dailyData.reduce(function(s, d) { return s + d.users; }, 0);
  const totalSessions = dailyData.reduce(function(s, d) { return s + d.sessions; }, 0);
  const totalPV = dailyData.reduce(function(s, d) { return s + d.pageviews; }, 0);
  const totalEngaged = dailyData.reduce(function(s, d) { return s + d.engaged; }, 0);
  const avgBounce = dailyData.length ? dailyData.reduce(function(s, d) { return s + d.bounce_rate; }, 0) / dailyData.length : 0;
  const avgDuration = dailyData.length ? dailyData.reduce(function(s, d) { return s + d.avg_duration; }, 0) / dailyData.length : 0;

  const reportDate = new Date().toISOString().split('T')[0];

  let md = '# ChinaBoundTravel - \u5468\u5ea6\u6570\u636e\u5206\u6790\u62a5\u544a\n\n';
  md += '> \u62a5\u544a\u751f\u6210\u65f6\u95f4\uff1a' + reportDate + '  \n';
  md += '> \u6570\u636e\u5468\u671f\uff1a' + dateRange.startDate + ' ~ ' + dateRange.endDate + '\n\n';
  md += '---\n\n';
  md += '## \u6838\u5fc3\u6307\u6807\u6982\u89c8\n\n';
  md += '| \u6307\u6807 | \u6570\u503c |\n|------|------|\n';
  md += '| \u6d3b\u8dc3\u7528\u6237 | ' + totalUsers.toLocaleString() + ' |\n';
  md += '| \u4f1a\u8bdd\u603b\u6570 | ' + totalSessions.toLocaleString() + ' |\n';
  md += '| \u9875\u9762\u6d4f\u89c8\u91cf | ' + totalPV.toLocaleString() + ' |\n';
  md += '| \u4e92\u52a8\u4f1a\u8bdd | ' + totalEngaged.toLocaleString() + ' |\n';
  md += '| \u5e73\u5747\u8df3\u51fa\u7387 | ' + avgBounce.toFixed(1) + '% |\n';
  md += '| \u5e73\u5747\u4f1a\u8bdd\u65f6\u957f | ' + fmtDuration(avgDuration) + ' |\n\n';
  md += '---\n\n';
  md += '## \u6bcf\u65e5\u8d8b\u52bf\n\n';
  md += '| \u65e5\u671f | \u8bbf\u5ba2\u6570 | \u4f1a\u8bdd\u6570 | \u6d4f\u89c8\u91cf | \u4e92\u52a8\u4f1a\u8bdd | \u8df3\u51fa\u7387 | \u5e73\u5747\u65f6\u957f |\n';
  md += '|------|--------|--------|--------|----------|--------|----------|\n';

  for (let i = 0; i < dailyData.length; i++) {
    const d = dailyData[i];
    md += '| ' + d.date + ' | ' + d.users + ' | ' + d.sessions + ' | ' + d.pageviews + ' | ' + d.engaged + ' | ' + d.bounce_rate.toFixed(1) + '% | ' + fmtDuration(d.avg_duration) + ' |\n';
  }

  if (dailyData.length >= 2) {
    const half = Math.floor(dailyData.length / 2);
    const firstHalf = dailyData.slice(0, half).reduce(function(s, d) { return s + d.users; }, 0);
    const secondHalf = dailyData.slice(half).reduce(function(s, d) { return s + d.users; }, 0);
    let trend = secondHalf > firstHalf ? '\u2b06\ufe0f \u4e0a\u5347' : secondHalf < firstHalf ? '\u2b07\ufe0f \u4e0b\u964d' : '\u27a1\ufe0f \u6301\u5e73';
    md += '\n> \u8d8b\u52bf\uff1a' + trend + '\uff08\u524d\u534a\u5468 ' + firstHalf + ' \u8bbf\u5ba2 \u2192 \u540e\u534a\u5468 ' + secondHalf + ' \u8bbf\u5ba2\uff09\n';
  }

  md += '\n---\n\n';
  md += '## \u70ed\u95e8\u9875\u9762 Top 10\n\n';
  md += '| # | \u9875\u9762\u6807\u9898 | \u8def\u5f84 | \u6d4f\u89c8\u91cf | \u4f1a\u8bdd\u6570 | \u8bbf\u5ba2\u6570 | \u5e73\u5747\u65f6\u957f |\n';
  md += '|---|----------|------|--------|--------|--------|----------|\n';

  for (let i = 0; i < Math.min(topPages.length, 10); i++) {
    const p = topPages[i];
    md += '| ' + (i+1) + ' | ' + p.title + ' | `' + p.path + '` | ' + p.views + ' | ' + p.sessions + ' | ' + p.users + ' | ' + fmtDuration(p.avg_time) + ' |\n';
  }

  md += '\n---\n\n';
  md += '## \u6d41\u91cf\u6765\u6e90\u6e20\u9053\n\n';
  md += '| \u6e20\u9053 | \u4f1a\u8bdd\u6570 | \u8bbf\u5ba2\u6570 | \u4e92\u52a8\u7387 |\n|------|--------|--------|--------|\n';

  for (let i = 0; i < sources.length; i++) {
    const s = sources[i];
    const cn = channelNames[s.channel] || s.channel;
    md += '| ' + cn + ' (' + s.channel + ') | ' + s.sessions + ' | ' + s.users + ' | ' + s.engagement.toFixed(1) + '% |\n';
  }

  md += '\n---\n\n';
  md += '## \u8bbf\u5ba2\u5730\u533a\u5206\u5e03 Top 10\n\n';
  md += '| \u56fd\u5bb6/\u5730\u533a | \u8bbf\u5ba2\u6570 | \u4f1a\u8bdd\u6570 | \u6d4f\u89c8\u91cf |\n|-----------|--------|--------|--------|\n';

  for (let i = 0; i < Math.min(countries.length, 10); i++) {
    const c = countries[i];
    md += '| ' + c.country + ' | ' + c.users + ' | ' + c.sessions + ' | ' + c.pageviews + ' |\n';
  }

  md += '\n---\n\n';
  md += '## \u8bbe\u5907\u5206\u5e03\n\n';
  md += '| \u8bbe\u5907\u7c7b\u578b | \u4f1a\u8bdd\u6570 | \u8bbf\u5ba2\u6570 | \u6d4f\u89c8\u91cf |\n|----------|--------|--------|--------|\n';

  for (let i = 0; i < devices.length; i++) {
    const d = devices[i];
    const cn = deviceNames[d.device.toLowerCase()] || d.device;
    md += '| ' + cn + ' | ' + d.sessions + ' | ' + d.users + ' | ' + d.pageviews + ' |\n';
  }

  md += '\n---\n\n';
  md += '## \u65b0\u8001\u8bbf\u5ba2\u6bd4\u4f8b\n\n';
  md += '| \u7c7b\u578b | \u4f1a\u8bdd\u6570 | \u8bbf\u5ba2\u6570 |\n|------|--------|--------|\n';

  for (let i = 0; i < userType.length; i++) {
    const u = userType[i];
    const cn = u.type === 'new' ? '\u65b0\u8bbf\u5ba2' : u.type === 'returning' ? '\u56de\u8bbf\u8bbf\u5ba2' : u.type;
    md += '| ' + cn + ' | ' + u.sessions + ' | ' + u.users + ' |\n';
  }

  // Insights
  md += '\n---\n\n## \u6d1e\u5bdf\u4e0e\u5efa\u8bae\n\n';
  const insights = [];

  if (topPages.length > 0) {
    insights.push('- **\u6700\u53d7\u6b22\u8fce\u9875\u9762**: "' + topPages[0].title + '"\uff08' + topPages[0].views + ' \u6b21\u6d4f\u89c8\uff09\u2014 \u8be5\u9875\u9762\u662f\u4e3b\u8981\u6d41\u91cf\u5165\u53e3\uff0c\u5efa\u8bae\u6301\u7eed\u4f18\u5316 SEO \u548c\u5185\u5bb9\u8d28\u91cf');
  }
  if (sources.length > 0) {
    const topSrc = sources[0];
    const topSrcCn = channelNames[topSrc.channel] || topSrc.channel;
    insights.push('- **\u6700\u5927\u6d41\u91cf\u6e20\u9053**: ' + topSrcCn + '\uff08' + topSrc.sessions + ' \u4e2a\u4f1a\u8bdd\uff09\u2014 \u662f\u5f53\u524d\u6700\u6709\u6548\u7684\u83b7\u5ba2\u6e20\u9053');
  }
  const newUsers = userType.find(function(u) { return u.type === 'new'; });
  if (newUsers && totalUsers > 0) {
    const newPct = (newUsers.users / totalUsers * 100).toFixed(1);
    if (parseFloat(newPct) > 60) {
      insights.push('- **\u65b0\u8bbf\u5ba2\u5360\u6bd4**: ' + newPct + '% \u2014 \u65b0\u7528\u6237\u83b7\u53d6\u80fd\u529b\u826f\u597d\uff0c\u5efa\u8bae\u5f3a\u5316\u8f6c\u5316\u5f15\u5bfc');
    } else {
      insights.push('- **\u65b0\u8bbf\u5ba2\u5360\u6bd4**: ' + newPct + '% \u2014 \u56de\u8bbf\u7528\u6237\u6bd4\u4f8b\u9ad8\uff0c\u7528\u6237\u7c98\u6027\u4e0d\u9519\uff0c\u5efa\u8bae\u589e\u52a0\u8ba2\u9605/\u4f1a\u5458\u5f15\u5bfc');
    }
  }
  if (avgBounce > 70) {
    insights.push('- \u26a0\ufe0f **\u8df3\u51fa\u7387\u504f\u9ad8** (' + avgBounce.toFixed(1) + '%) \u2014 \u5efa\u8bae\u4f18\u5316\u843d\u5730\u9875\u52a0\u8f7d\u901f\u5ea6\u548c\u9996\u5c4f\u5185\u5bb9');
  } else if (avgBounce < 40 && avgBounce > 0) {
    insights.push('- \u2705 **\u8df3\u51fa\u7387\u5065\u5eb7** (' + avgBounce.toFixed(1) + '%) \u2014 \u7528\u6237\u7559\u5b58\u8868\u73b0\u826f\u597d');
  }
  const mobileSess = devices.find(function(d) { return d.device.toLowerCase() === 'mobile'; });
  const desktopSess = devices.find(function(d) { return d.device.toLowerCase() === 'desktop'; });
  if (mobileSess && desktopSess && mobileSess.sessions > desktopSess.sessions) {
    insights.push('- \ud83d\udcf1 **\u79fb\u52a8\u7aef\u6d41\u91cf\u9886\u5148** \u2014 \u786e\u4fdd\u79fb\u52a8\u4f53\u9a8c\u4f18\u5316\uff08\u52a0\u8f7d\u901f\u5ea6\u3001\u4ea4\u4e92\u53cb\u597d\u5ea6\uff09');
  } else if (mobileSess && desktopSess) {
    insights.push('- \ud83d\udcbb **\u684c\u9762\u7aef\u6d41\u91cf\u9886\u5148** \u2014 \u53ef\u4ee5\u9002\u5f53\u52a0\u5f3a\u79fb\u52a8\u7aef\u5185\u5bb9\u9002\u914d');
  }

  md += insights.join('\n');
  md += '\n\n---\n\n';
  md += '> \u6570\u636e\u6765\u6e90\uff1aGoogle Analytics 4 (Property ID: ' + data.propertyId + ')  \n';
  md += '> \u7531 GA4 Analytics Data API \u81ea\u52a8\u751f\u6210\n';

  // Save
  const outDir = path.dirname(OUTPUT);
  try { fs.mkdirSync(outDir, { recursive: true }); } catch(e) {}
  fs.writeFileSync(OUTPUT, md, 'utf8');

  console.log('\nReport saved to: ' + OUTPUT);
  console.log('\n--- Quick Summary ---');
  console.log('Total Users: ' + totalUsers);
  console.log('Total Sessions: ' + totalSessions);
  console.log('Total Pageviews: ' + totalPV);
  console.log('Avg Bounce Rate: ' + avgBounce.toFixed(1) + '%');
  console.log('Avg Session Duration: ' + fmtDuration(avgDuration));
  if (topPages.length > 0) console.log('Top Page: ' + topPages[0].title + ' (' + topPages[0].views + ' views)');
  if (sources.length > 0) console.log('Top Source: ' + sources[0].channel + ' (' + sources[0].sessions + ' sessions)');
  if (countries.length > 0) console.log('Top Country: ' + countries[0].country + ' (' + countries[0].users + ' users)');
}

main().catch(function(err) {
  console.error('Error:', err.message);
  process.exit(1);
});
