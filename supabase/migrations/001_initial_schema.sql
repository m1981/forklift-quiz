-- Enable UUID extension (optional, keeping for future use)
create extension if not exists "uuid-ossp";

-- 1. Tables
create table if not exists questions (
    id text primary key,
    category text default 'Ogólne',
    json_data jsonb not null
);

create table if not exists user_profiles (
    user_id text primary key,
    streak_days int default 0,
    last_login date,
    daily_goal int default 3,
    daily_progress int default 0,
    last_daily_reset date,
    has_completed_onboarding boolean default false,
    preferred_language text default 'pl',
    metadata jsonb default '{}'::jsonb
);

create table if not exists user_progress (
    user_id text,
    question_id text references questions(id),
    is_correct boolean,
    consecutive_correct int default 0,
    timestamp timestamptz default now(),
    primary key (user_id, question_id)
);

-- 2. Indexes for performance
create index if not exists idx_questions_category on questions(category);
create index if not exists idx_user_progress_user_id on user_progress(user_id);
create index if not exists idx_user_progress_timestamp on user_progress(timestamp);

-- 3. RPC: Submit Attempt (Atomic Streak Calculation)
create or replace function submit_attempt(
    p_user_id text,
    p_question_id text,
    p_is_correct boolean
)
returns void as $$
declare
    v_current_streak int;
begin
    select consecutive_correct into v_current_streak
    from user_progress
    where user_id = p_user_id and question_id = p_question_id;

    if not found then v_current_streak := 0; end if;

    if p_is_correct then
        v_current_streak := v_current_streak + 1;
    else
        v_current_streak := 0;
    end if;

    insert into user_progress (user_id, question_id, is_correct, consecutive_correct, timestamp)
    values (p_user_id, p_question_id, p_is_correct, v_current_streak, now())
    on conflict (user_id, question_id)
    do update set
        is_correct = excluded.is_correct,
        consecutive_correct = excluded.consecutive_correct,
        timestamp = excluded.timestamp;
end;
$$ language plpgsql;

-- 4. RPC: Get Repetition Candidates (Spaced Repetition Logic)
create or replace function get_repetition_candidates(
    p_user_id text,
    p_threshold int
)
returns table (json_data jsonb, streak int, seen boolean) as $$
begin
    return query
    select
        q.json_data,
        coalesce(up.consecutive_correct, 0) as streak,
        (up.question_id is not null) as seen
    from questions q
    left join user_progress up
        on q.id = up.question_id and up.user_id = p_user_id
    where
        up.question_id is null
        or up.consecutive_correct < p_threshold
        or (
            up.consecutive_correct >= p_threshold
            and up.timestamp < (now() - interval '3 days')
        );
end;
$$ language plpgsql;

-- 5. RPC: Get Category Stats
create or replace function get_category_stats(
    p_user_id text,
    p_threshold int
)
returns table (category text, total bigint, mastered bigint) as $$
begin
    return query
    select
        q.category,
        count(q.id) as total,
        sum(case when coalesce(up.consecutive_correct, 0) >= p_threshold then 1 else 0 end) as mastered
    from questions q
    left join user_progress up
        on q.id = up.question_id and up.user_id = p_user_id
    group by q.category;
end;
$$ language plpgsql;
