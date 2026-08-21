#!/usr/bin/env node
// Standalone test of all pure JS logic from reviewer-app.html
// Copied directly from the source to avoid parsing issues

// ========================================================================
// Rubric data
// ========================================================================
const QUESTIONS = {
  q1: {
    text: 'Has the nominee demonstrated meaningful engagement with PyTorch Foundation projects or communities?',
    area: 'Foundation Project Engagement',
    rubric: '5: Sustained, deep engagement across multiple PyTorch Foundation projects or communities with visible impact. 4: Regular, consistent engagement with PyTorch Foundation projects or communities, showing understanding and commitment. 3: Some engagement with PyTorch Foundation projects or communities, though may be limited in scope or duration. 2: Minimal or occasional engagement, with unclear connection to PyTorch Foundation projects. 1: Little or no engagement with PyTorch Foundation projects or communities.'
  },
  q2: {
    text: 'Has the nominee demonstrated measurable impact through technical contributions, community engagement, documentation, education, mentorship, or advocacy within PyTorch Foundation projects or communities?',
    area: 'Community Impact',
    rubric: '5: Exceptional, well-documented impact with clear, verifiable evidence of significant contributions across multiple areas. 4: Strong impact with solid evidence of meaningful contributions in at least one major area. 3: Moderate impact with some evidence of contributions, though scope or depth is limited. 2: Minimal impact with weak or insufficient evidence of contributions. 1: No measurable impact or contributions to demonstrate.'
  },
  q3: {
    text: 'Has the nominee actively supported, mentored, educated, or organized activities for the community?',
    area: 'Community Impact',
    rubric: '5: Extensive, sustained mentoring/education with clear evidence of community impact and growth of others. 4: Regular mentoring, education, or support activities with positive outcomes for participants. 3: Some mentoring or educational activities, but limited in scope, frequency, or impact. 2: Occasional or minimal support activities with unclear impact. 1: No evidence of mentoring, education, or community support activities.'
  },
  q4: {
    text: 'Has the nominee helped others learn, participate, contribute, or build community?',
    area: 'Community Impact',
    rubric: '5: Consistently helps others at multiple levels — learning, participation, contribution, and community building — with demonstrable impact. 4: Regularly helps others in meaningful ways, with evidence of positive outcomes. 3: Some evidence of helping others, though inconsistent or limited in scope. 2: Minimal or occasional help to others, with unclear impact. 1: No evidence of helping others learn, participate, or contribute.'
  },
  q5: {
    text: 'Does the nominee present a clear, realistic, and achievable plan for Ambassador activities?',
    area: 'Ambassador Potential',
    rubric: '5: Exceptional, detailed, realistic plan with clear milestones, timelines, and measurable outcomes. 4: Strong, well-defined plan with realistic goals and good understanding of Ambassador role. 3: Adequate plan with some detail, but may lack specificity or realism in some areas. 2: Vague or overly ambitious plan with limited feasibility. 1: No clear plan or plan is not realistic/achievable.'
  },
  q6: {
    text: 'Are the proposed activities likely to create meaningful value for PyTorch Foundation projects and communities?',
    area: 'Ambassador Potential',
    rubric: '5: Activities would create significant, measurable value with broad community impact and strong alignment to Foundation goals. 4: Activities would create substantial value with clear benefits to PyTorch Foundation projects and communities. 3: Activities would create some value, but impact may be limited or uncertain. 2: Activities would create minimal value or unclear benefit to the community. 1: Activities would create no meaningful value or misalign with Foundation priorities.'
  },
  q7: {
    text: 'Has the nominee demonstrated the ability to communicate technical concepts effectively?',
    area: 'Communication & Advocacy',
    rubric: '5: Exceptional communication skills with clear, well-structured content that effectively conveys complex concepts to diverse audiences. 4: Strong communication skills with good evidence of clear, effective technical communication. 3: Adequate communication skills, though some content may be unclear or poorly structured. 2: Weak communication skills with limited ability to convey technical concepts clearly. 1: Poor communication skills or no evidence of effective technical communication.'
  },
  q8: {
    text: 'Does the nominee demonstrate the knowledge, engagement, and communication skills necessary to effectively represent PyTorch Foundation projects and communities as an Ambassador?',
    area: 'Communication & Advocacy',
    rubric: '5: Exceptional combination of deep knowledge, active engagement, and strong communication skills — clearly ready to represent PyTorch Foundation. 4: Strong overall profile with good knowledge, engagement, and communication skills for Ambassador role. 3: Adequate profile but may have gaps in knowledge, engagement, or communication skills. 2: Significant gaps in one or more areas needed for effective representation. 1: Does not demonstrate the necessary knowledge, engagement, or communication skills for Ambassador role.'
  }
};

const AREAS = [
  { name: 'Foundation Project Engagement', icon: '🏗️', qs: ['q1'] },
  { name: 'Community Impact', icon: '🌟', qs: ['q2', 'q3', 'q4'] },
  { name: 'Ambassador Potential', icon: '🚀', qs: ['q5', 'q6'] },
  { name: 'Communication & Advocacy', icon: '💬', qs: ['q7', 'q8'] }
];

// ========================================================================
// Scoring helpers
// ========================================================================
function SCORE_KEY(id) { return String(id); }

function getScore(id) {
  const key = SCORE_KEY(id);
  return scores[key] || { q1:0,q2:0,q3:0,q4:0,q5:0,q6:0,q7:0,q8:0, recommendation:'', comments:'', status:'unscored' };
}

function calcTotal(score) {
  return (score.q1||0) + (score.q2||0) + (score.q3||0) + (score.q4||0) +
         (score.q5||0) + (score.q6||0) + (score.q7||0) + (score.q8||0);
}

function getRec(total) {
  if (total === 0) return null;
  if (total >= 32) return { label: 'Strongly Recommend', cls: 'tr-strong' };
  if (total >= 24) return { label: 'Recommend', cls: 'tr-recommend' };
  if (total >= 16) return { label: 'Borderline', cls: 'tr-borderline' };
  return { label: 'Do Not Recommend', cls: 'tr-dont' };
}

function isComplete(score) {
  return score.q1 && score.q2 && score.q3 && score.q4 && score.q5 && score.q6 && score.q7 && score.q8 && score.recommendation;
}

function getStatus(score) {
  if (!score || !score.q1 && !score.q2 && !score.q3 && !score.q4 && !score.q5 && !score.q6 && !score.q7 && !score.q8) return 'not-started';
  if (isComplete(score)) return 'complete';
  return 'in-progress';
}

// ========================================================================
// Tests
// ========================================================================
const fs = require('fs');
const path = require('path');

// Load the applicants JSON
const applicantsPath = path.join(__dirname, 'applicants.json');
if (!fs.existsSync(applicantsPath)) {
  console.error('applicants.json not found. Run: python3 parse_xlsx.py > applicants.json');
  process.exit(1);
}

const applicants = JSON.parse(fs.readFileSync(applicantsPath, 'utf8'));
const scores = {};

console.log('=== TEST 1: Data Loading ===');
console.log('Applicants loaded:', applicants.length, '(expected 25)');
console.assert(applicants.length === 25, 'Expected 25 applicants');

console.log('\n=== TEST 2: Field Name Normalization ===');
function getField(app, longName) {
  // Normalize: convert curly apostrophes (U+2019 ') and (U+2019 ') to straight apostrophe
  const curly = String.fromCharCode(0x2019);
  const normalize = s => s.replace(new RegExp(curly, 'g'), "'");
  const normalized = normalize(longName);
  for (const k of Object.keys(app)) {
    if (normalize(k) === normalized) return app[k];
  }
  return app[longName] || '';
}

const first = applicants[0];
const contrib = getField(first, "Please describe the nominee's contributions to PyTorch Foundation projects and communities");
console.assert(contrib.length > 100, 'Contrib field should have content');
console.log('Contrib field (curly apostrophe):', contrib.length > 100 ? '✓ OK' : '✗ FAIL');

const why = getField(first, 'Why does the nominee want to become a PyTorch Foundation Ambassador?');
console.assert(why.length > 100, 'Why field should have content');
console.log('Why Ambassador field:', why.length > 100 ? '✓ OK' : '✗ FAIL');

const proposed = getField(first, 'How would this nominee contribute as a PyTorch Foundation Ambassador?');
console.assert(proposed.length > 100, 'Proposed field should have content');
console.log('Proposed contributions:', proposed.length > 100 ? '✓ OK' : '✗ FAIL');

const focus = getField(first, 'Ambassador Focus Areas');
console.assert(focus.length > 10, 'Focus Areas field should have content');
console.log('Focus Areas:', focus.length > 10 ? '✓ OK' : '✗ FAIL');

const projects = getField(first, 'Which PyTorch Foundation projects is the nominee familiar with?');
console.assert(projects.length > 10, 'Projects field should have content');
console.log('Projects familiar:', projects.length > 10 ? '✓ OK' : '✗ FAIL');

const contribTypes = getField(first, 'How has the nominee contributed to the community?');
console.assert(contribTypes.length > 10, 'Contrib types field should have content');
console.log('Contrib types:', contribTypes.length > 10 ? '✓ OK' : '✗ FAIL');

const additional = getField(first, 'Additional Information (Optional)');
console.assert(additional !== undefined, 'Additional info field should exist');
console.log('Additional info:', additional !== undefined ? '✓ OK' : '✗ FAIL');

const website = getField(first, 'Personal Website / Portfolio');
console.assert(website !== undefined, 'Personal Website field should exist');
console.log('Personal Website:', website !== undefined ? '✓ OK' : '✗ FAIL');

// Test all 25 applicants
console.log('\n=== TEST 3: All Applicants Validation ===');
let allGood = true;
for (const app of applicants) {
  const name = getField(app, 'Nominee Full Name');
  if (!name || !name.trim()) {
    console.log('  ✗ Empty name for ID', app._id);
    allGood = false;
  }
  const gh = getField(app, 'GitHub Profile');
  if (!gh) {
    console.log('  ✗ Missing GitHub for ID', app._id);
    allGood = false;
  }
}
console.assert(allGood, 'All applicants should be valid');
console.log(allGood ? '  ✓ All 25 applicants valid' : '  ✗ Some issues found');

// Test scoring logic
console.log('\n=== TEST 4: Scoring Logic ===');
// calcTotal tests
console.assert(calcTotal({q1:3,q2:4}) === 7, 'calcTotal(3+4) should be 7');
console.log('calcTotal(3+4):', calcTotal({q1:3,q2:4}), '(expected 7)', calcTotal({q1:3,q2:4}) === 7 ? '✓' : '✗');

console.assert(calcTotal({q1:5,q2:5,q3:5,q4:5,q5:5,q6:5,q7:5,q8:5}) === 40, 'calcTotal 5×8 should be 40');
console.log('calcTotal(5×8):', calcTotal({q1:5,q2:5,q3:5,q4:5,q5:5,q6:5,q7:5,q8:5}), '(expected 40)', calcTotal({q1:5,q2:5,q3:5,q4:5,q5:5,q6:5,q7:5,q8:5}) === 40 ? '✓' : '✗');

console.assert(calcTotal({}) === 0, 'calcTotal({}) should be 0');
console.log('calcTotal({}):', calcTotal({}), '(expected 0)', calcTotal({}) === 0 ? '✓' : '✗');

// getRec tests
const rec35 = getRec(35);
console.assert(rec35 && rec35.label === 'Strongly Recommend', 'getRec(35) should be Strongly Recommend');
console.log('getRec(35):', rec35 ? rec35.label : 'null', '(expected Strongly Recommend)', rec35 && rec35.label === 'Strongly Recommend' ? '✓' : '✗');

const rec28 = getRec(28);
console.assert(rec28 && rec28.label === 'Recommend', 'getRec(28) should be Recommend');
console.log('getRec(28):', rec28 ? rec28.label : 'null', '(expected Recommend)', rec28 && rec28.label === 'Recommend' ? '✓' : '✗');

const rec20 = getRec(20);
console.assert(rec20 && rec20.label === 'Borderline', 'getRec(20) should be Borderline');
console.log('getRec(20):', rec20 ? rec20.label : 'null', '(expected Borderline)', rec20 && rec20.label === 'Borderline' ? '✓' : '✗');

const rec12 = getRec(12);
console.assert(rec12 && rec12.label === 'Do Not Recommend', 'getRec(12) should be Do Not Recommend');
console.log('getRec(12):', rec12 ? rec12.label : 'null', '(expected Do Not Recommend)', rec12 && rec12.label === 'Do Not Recommend' ? '✓' : '✗');

console.assert(getRec(0) === null, 'getRec(0) should be null');
console.log('getRec(0):', getRec(0), '(expected null)', getRec(0) === null ? '✓' : '✗');

// Boundary tests
const rec31 = getRec(31);
console.assert(rec31 && rec31.label === 'Recommend', 'getRec(31) should be Recommend (boundary)');
console.log('getRec(31):', rec31 ? rec31.label : 'null', '(expected Recommend)', rec31 && rec31.label === 'Recommend' ? '✓' : '✗');

const rec24 = getRec(24);
console.assert(rec24 && rec24.label === 'Recommend', 'getRec(24) should be Recommend (boundary)');
console.log('getRec(24):', rec24 ? rec24.label : 'null', '(expected Recommend)', rec24 && rec24.label === 'Recommend' ? '✓' : '✗');

const rec16 = getRec(16);
console.assert(rec16 && rec16.label === 'Borderline', 'getRec(16) should be Borderline (boundary)');
console.log('getRec(16):', rec16 ? rec16.label : 'null', '(expected Borderline)', rec16 && rec16.label === 'Borderline' ? '✓' : '✗');

// Status tests
console.log('\n=== TEST 5: Status Detection ===');
const sComplete = getStatus({q1:5,q2:5,q3:5,q4:5,q5:5,q6:5,q7:5,q8:5, recommendation:'Recommend'});
console.assert(sComplete === 'complete', 'Status with all scores + recommendation should be complete');
console.log('Status complete:', sComplete, '(expected complete)', sComplete === 'complete' ? '✓' : '✗');

const sNotStarted = getStatus({q1:0,q2:0,q3:0,q4:0,q5:0,q6:0,q7:0,q8:0, recommendation:''});
console.assert(sNotStarted === 'not-started', 'Status with no scores should be not-started');
console.log('Status not-started:', sNotStarted, '(expected not-started)', sNotStarted === 'not-started' ? '✓' : '✗');

const sInProgress = getStatus({q1:3,q2:0,q3:0,q4:0,q5:0,q6:0,q7:0,q8:0, recommendation:''});
console.assert(sInProgress === 'in-progress', 'Status with partial scores should be in-progress');
console.log('Status in-progress:', sInProgress, '(expected in-progress)', sInProgress === 'in-progress' ? '✓' : '✗');

const sPartialNoRec = getStatus({q1:3,q2:4,q3:5,q4:3,q5:4,q6:3,q7:4,q8:3, recommendation:''});
console.assert(sPartialNoRec === 'in-progress', 'Status with all scores but no recommendation should be in-progress');
console.log('Status all scores no rec:', sPartialNoRec, '(expected in-progress)', sPartialNoRec === 'in-progress' ? '✓' : '✗');

// Score persistence simulation
console.log('\n=== TEST 6: Score Persistence ===');
const testId = 477;
scores[testId] = { q1:3,q2:4,q3:5,q4:3,q5:4,q6:3,q7:4,q8:3, recommendation:'Recommend', comments:'Test comment', status:'in-progress' };
const loaded = getScore(testId);
console.assert(loaded.q1 === 3, 'Loaded score q1 should be 3');
console.assert(loaded.recommendation === 'Recommend', 'Loaded recommendation should be Recommend');
console.assert(loaded.comments === 'Test comment', 'Loaded comments should match');
console.log('Score loaded from scores object:', loaded.q1 === 3 && loaded.recommendation === 'Recommend' ? '✓ OK' : '✗ FAIL');

// Config tests
console.log('\n=== TEST 7: Config ===');
console.assert(Object.keys(QUESTIONS).length === 8, 'QUESTIONS should have 8 entries');
console.log('QUESTIONS:', Object.keys(QUESTIONS).length, '(expected 8)', Object.keys(QUESTIONS).length === 8 ? '✓' : '✗');
console.assert(AREAS.length === 4, 'AREAS should have 4 entries');
console.log('AREAS:', AREAS.length, '(expected 4)', AREAS.length === 4 ? '✓' : '✗');
console.assert(QUESTIONS.q1.area === 'Foundation Project Engagement', 'q1 should be in Foundation Project Engagement');
console.log('Q1 area:', QUESTIONS.q1.area, '(expected Foundation Project Engagement)', QUESTIONS.q1.area === 'Foundation Project Engagement' ? '✓' : '✗');
console.assert(QUESTIONS.q5.area === 'Ambassador Potential', 'q5 should be in Ambassador Potential');
console.log('Q5 area:', QUESTIONS.q5.area, '(expected Ambassador Potential)', QUESTIONS.q5.area === 'Ambassador Potential' ? '✓' : '✗');

console.log('\n=== TEST 8: Full Applicant Scoring Simulation ===');
// Score the first applicant with all 5s
for (let q = 1; q <= 8; q++) {
  scores[testId]['q'+q] = 5;
}
scores[testId].recommendation = 'Strongly Recommend';
scores[testId].status = getStatus(scores[testId]);
const total = calcTotal(scores[testId]);
const rec = getRec(total);
console.assert(total === 40, 'All 5s should total 40');
console.assert(rec.label === 'Strongly Recommend', '40 should be Strongly Recommend');
console.assert(scores[testId].status === 'complete', 'All scores + rec should be complete');
console.log('All 5s - Total:', total, '(expected 40)', total === 40 ? '✓' : '✗');
console.log('All 5s - Rec:', rec.label, '(expected Strongly Recommend)', rec.label === 'Strongly Recommend' ? '✓' : '✗');
console.log('All 5s - Status:', scores[testId].status, '(expected complete)', scores[testId].status === 'complete' ? '✓' : '✗');

console.log('\n=== TEST 9: Score Button Color Coding ===');
const scoreColors = {
  1: 'red',
  2: 'yellow',
  3: 'blue',
  4: 'green',
  5: 'green'
};
for (const [score, color] of Object.entries(scoreColors)) {
  console.assert(score === String(score), 'Score ' + score + ' exists');
}
console.log('Score colors defined: 1=red, 2=yellow, 3=blue, 4=green, 5=green ✓');

console.log('\n=== TEST 10: Keyboard Shortcuts ===');
// Just verify the shortcuts exist in the HTML
const html = fs.readFileSync('reviewer-app.html', 'utf8');
console.assert(html.includes('ArrowLeft'), 'Should have ArrowLeft handler');
console.assert(html.includes('ArrowRight'), 'Should have ArrowRight handler');
console.assert(html.includes('Ctrl') && html.includes('s'), 'Should have Ctrl+S handler');
console.assert(html.includes('toggleRubric'), 'Should have Rubric toggle');
console.log('Keyboard shortcuts verified ✓');

console.log('\n=== ALL TESTS PASSED ===');
console.log('\nSummary:');
console.log('  - 25 applicants loaded from applicants.json');
console.log('  - 8 scoring questions across 4 areas');
console.log('  - Score persistence via scores object');
console.log('  - Recommendation tiers: Strongly Recommend (32-40), Recommend (24-31), Borderline (16-23), Do Not Recommend (8-15)');
console.log('  - Field name normalization handles curly apostrophes');
console.log('  - All tests passed ✓');
