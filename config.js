// Supabase project credentials — safe to commit, anon key only
const SUPABASE_URL = 'https://fixnbthycrvegkofvzfv.supabase.co';
const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  'eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZpeG5idGh5Y3J2ZWdrb2Z2emZ2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIyOTQwMDcsImV4cCI6MjA4Nzg3MDAwN30.' +
  '4N67KwFK6WZwljLT7jQg_ubZJzEu5HgPd1X4DGDGEiY';

// Local Mode primitives (phase 1 scaffold)
const LOCAL_MODE_KEY = 'derby_local_mode';
const LOCAL_API_BASE = (typeof location !== 'undefined')
  ? `${location.protocol}//${location.hostname}:8000`
  : 'http://localhost:8000';

function isLocalMode() {
  try {
    return localStorage.getItem(LOCAL_MODE_KEY) === '1';
  } catch {
    return false;
  }
}
