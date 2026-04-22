-- Execute este SQL no Supabase: Dashboard > SQL Editor > New query

create table gastos (
  id          uuid primary key default gen_random_uuid(),
  valor       decimal(10, 2) not null,
  data        date not null,
  estabelecimento text not null,
  categoria   text not null,
  criado_em   timestamptz default now()
);

-- Índices para filtros comuns
create index idx_gastos_data      on gastos (data);
create index idx_gastos_categoria on gastos (categoria);
