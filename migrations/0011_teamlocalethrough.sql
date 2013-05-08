CREATE TABLE `life_teamlocalethrough` (
    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `start` datetime,
    `end` datetime,
    `team_id` integer NOT NULL,
    `locale_id` integer NOT NULL,
    UNIQUE (`start`, `end`, `team_id`, `locale_id`)
)
;
ALTER TABLE `life_teamlocalethrough` ADD CONSTRAINT `team_id_refs_id_916bb46a` FOREIGN KEY (`team_id`) REFERENCES `life_locale` (`id`);
ALTER TABLE `life_teamlocalethrough` ADD CONSTRAINT `locale_id_refs_id_916bb46a` FOREIGN KEY (`locale_id`) REFERENCES `life_locale` (`id`);
CREATE INDEX `life_teamlocalethrough_fcf8ac47` ON `life_teamlocalethrough` (`team_id`);
CREATE INDEX `life_teamlocalethrough_5cee98e0` ON `life_teamlocalethrough` (`locale_id`);
