drop table if exists users;
create table users (
  profileId string primary key,
  profAccountId string not null,
  profSavedataId string not null,
  pushoverUserAPI string not null,
  timestamp string not null
);