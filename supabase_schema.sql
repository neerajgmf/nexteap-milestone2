-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Create reviews table
create table if not exists reviews (
  id uuid primary key default uuid_generate_v4(),
  source text not null check (source in ('Google Play', 'App Store')),
  review_id text not null, -- External ID from the store
  reviewer_name text,
  rating integer check (rating >= 1 and rating <= 5),
  date timestamptz not null,
  content text,
  thumbs_up_count integer default 0,
  app_version text,
  developer_response text,
  developer_response_date timestamptz,
  
  -- Analysis fields
  sentiment_score float,
  sentiment_label text,
  topics text[], -- Array of topics/themes
  
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  
  -- Ensure unique reviews per source
  unique(source, review_id)
);

-- Create indexes for common queries
create index if not exists idx_reviews_date on reviews(date desc);
create index if not exists idx_reviews_rating on reviews(rating);
create index if not exists idx_reviews_source on reviews(source);
create index if not exists idx_reviews_sentiment on reviews(sentiment_label);

-- Enable Row Level Security (RLS)
alter table reviews enable row level security;

-- Create policy to allow public read access (if needed, or restrict to authenticated)
create policy "Allow public read access" on reviews for select using (true);

-- Create policy to allow service role to insert/update (implicit, but good to be explicit if using anon)
-- For now, we assume the scraper runs with service_role key which bypasses RLS.
