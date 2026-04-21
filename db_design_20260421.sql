CREATE TABLE `role` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(30) UNIQUE NOT NULL
);

CREATE TABLE `permission` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `code` varchar(30) UNIQUE NOT NULL,
  `name` varchar(30) UNIQUE NOT NULL
);

CREATE TABLE `role_permission` (
  `role_id` integer,
  `permission_id` integer,
  PRIMARY KEY (`role_id`, `permission_id`)
);

CREATE TABLE `admin` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `password` varchar(500) NOT NULL,
  `email` varchar(100) UNIQUE NOT NULL,
  `name` varchar(30),
  `phone` varchar(30),
  `role_id` integer,
  `status` VARCHAR(30) NOT NULL DEFAULT 'enabled',
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `member` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `password` varchar(500) NOT NULL,
  `email` varchar(100) UNIQUE NOT NULL,
  `name` varchar(30),
  `phone` varchar(30),
  `region` varchar(30),
  `locality` varchar(30),
  `address` varchar(100),
  `status` VARCHAR(30) NOT NULL DEFAULT 'enabled',
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `category` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(100) NOT NULL
);

CREATE TABLE `product` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `category_id` integer,
  `name` varchar(100) NOT NULL,
  `price` integer NOT NULL DEFAULT 100,
  `stock` integer NOT NULL DEFAULT 0,
  `description` varchar(2000),
  `status` VARCHAR(30) NOT NULL DEFAULT 'unlisted',
  `recommended` bool NOT NULL DEFAULT 0,
  `is_deleted` bool NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `image` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `product_id` integer,
  `description` varchar(100),
  `url` varchar(500),
  `sort_order` integer,
  `is_primary` bool NOT NULL DEFAULT 0
);

CREATE TABLE `cart` (
  `member_id` integer,
  `product_id` integer,
  `qty` integer NOT NULL DEFAULT 1,
  `updated_at` timestamp NOT NULL,
  PRIMARY KEY (`member_id`, `product_id`)
);

CREATE TABLE `orders` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `member_id` integer NOT NULL,
  `rcpt_name` varchar(30) NOT NULL,
  `rcpt_phone` VARCHAR(30) NOT NULL,
  `rcpt_region` varchar(30) NOT NULL,
  `rcpt_locality` varchar(30) NOT NULL,
  `rcpt_address` varchar(100) NOT NULL,
  `total` integer NOT NULL,
  `pay_status` VARCHAR(30) NOT NULL DEFAULT 'unpaid',
  `ship_status` VARCHAR(30) NOT NULL DEFAULT 'pending',
  `is_deleted` bool NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `order_item` (
  `order_id` integer,
  `product_id` integer,
  `name` varchar(100) NOT NULL,
  `qty` integer NOT NULL,
  `price` integer NOT NULL,
  PRIMARY KEY (`order_id`, `product_id`)
);

CREATE TABLE `inquiry` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `member_id` integer NOT NULL,
  `member_read` bool NOT NULL,
  `admin_read` bool NOT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `message` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `inquiry_id` integer NOT NULL,
  `sender_type` varchar(30) NOT NULL,
  `admin_id` integer,
  `content` varchar(2000) NOT NULL,
  `created_at` timestamp NOT NULL
);

ALTER TABLE `role_permission` ADD FOREIGN KEY (`role_id`) REFERENCES `role` (`id`);

ALTER TABLE `role_permission` ADD FOREIGN KEY (`permission_id`) REFERENCES `permission` (`id`);

ALTER TABLE `admin` ADD FOREIGN KEY (`role_id`) REFERENCES `role` (`id`);

ALTER TABLE `product` ADD FOREIGN KEY (`category_id`) REFERENCES `category` (`id`);

ALTER TABLE `image` ADD FOREIGN KEY (`product_id`) REFERENCES `product` (`id`);

ALTER TABLE `cart` ADD FOREIGN KEY (`member_id`) REFERENCES `member` (`id`);

ALTER TABLE `cart` ADD FOREIGN KEY (`product_id`) REFERENCES `product` (`id`);

ALTER TABLE `orders` ADD FOREIGN KEY (`member_id`) REFERENCES `member` (`id`);

ALTER TABLE `order_item` ADD FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`);

ALTER TABLE `order_item` ADD FOREIGN KEY (`product_id`) REFERENCES `product` (`id`);

ALTER TABLE `inquiry` ADD FOREIGN KEY (`member_id`) REFERENCES `member` (`id`);

ALTER TABLE `message` ADD FOREIGN KEY (`inquiry_id`) REFERENCES `inquiry` (`id`);

ALTER TABLE `message` ADD FOREIGN KEY (`admin_id`) REFERENCES `admin` (`id`);
