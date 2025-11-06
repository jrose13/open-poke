import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://erjabdqbgancubnqwcdl.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVyamFiZHFiZ2FuY3VibnF3Y2RsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI0Mzc4NjEsImV4cCI6MjA3ODAxMzg2MX0.thYMfwQHm7Tj4kbmWK8NG79muUkt8trx0ev1rcCxd7w';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

