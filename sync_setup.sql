-- 台股估值看板：雲端同步後端（Supabase 免費方案）
-- 在 Supabase 專案 → SQL Editor → New query 貼上整段 → Run。只需執行一次。
create table if not exists public.sync (
  code text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);
-- 開 RLS 但不給任何 policy：anon key 不能直接讀整張表（列不出所有配對碼），只能透過下面兩個函式
alter table public.sync enable row level security;

create or replace function public.sync_get(p_code text)
returns jsonb language sql security definer set search_path = public as $$
  select jsonb_build_object('data', data, 'updated_at', updated_at)
  from public.sync where code = p_code;
$$;

create or replace function public.sync_put(p_code text, p_data jsonb)
returns timestamptz language plpgsql security definer set search_path = public as $$
declare ts timestamptz;
begin
  if length(p_code) <> 14 or pg_column_size(p_data) > 60000 then
    raise exception 'bad input';
  end if;
  insert into public.sync(code, data, updated_at) values (p_code, p_data, now())
  on conflict (code) do update set data = excluded.data, updated_at = now()
  returning updated_at into ts;
  return ts;
end $$;

grant execute on function public.sync_get(text) to anon;
grant execute on function public.sync_put(text, jsonb) to anon;
