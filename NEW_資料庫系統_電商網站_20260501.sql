CREATE TABLE `customer` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `password` varchar(255) NOT NULL,
  `email` varchar(100) UNIQUE NOT NULL,
  `name` varchar(30) NOT NULL,
  `phone` varchar(30),
  `region` varchar(30),
  `locality` varchar(30),
  `address` varchar(100),
  `is_active` bool NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `wishlist` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `customer_id` int UNIQUE NOT NULL,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `wishlist_item` (
  `wishlist_id` int NOT NULL,
  `product_id` int NOT NULL,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL,
  PRIMARY KEY (`wishlist_id`, `product_id`)
);

CREATE TABLE `cart` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `customer_id` int UNIQUE NOT NULL,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `cart_item` (
  `cart_id` int NOT NULL,
  `sku_id` int NOT NULL,
  `qty` int NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL,
  PRIMARY KEY (`cart_id`, `sku_id`)
);

CREATE TABLE `promo_code` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `code` varchar(30) UNIQUE NOT NULL,
  `description` varchar(100),
  `discount_type` varchar(30) NOT NULL,
  `discount_value` decimal(12,2) NOT NULL,
  `is_active` bool NOT NULL DEFAULT 1,
  `start_at` timestamp NOT NULL,
  `end_at` timestamp NOT NULL,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `promo_code_category` (
  `promo_code_id` int,
  `category_id` int,
  PRIMARY KEY (`promo_code_id`, `category_id`)
);

CREATE TABLE `promo_code_product` (
  `promo_code_id` int,
  `product_id` int,
  PRIMARY KEY (`promo_code_id`, `product_id`)
);

CREATE TABLE `orders` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `customer_id` int NOT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'pending',
  `subtotal` decimal(12,2) NOT NULL,
  `discount_total` decimal(12,2) NOT NULL,
  `shipping_fee` decimal(12,2) NOT NULL,
  `total` decimal(12,2) NOT NULL,
  `name` varchar(30) NOT NULL,
  `phone` VARCHAR(30) NOT NULL,
  `region` varchar(30) NOT NULL,
  `locality` varchar(30) NOT NULL,
  `address` varchar(100) NOT NULL,
  `promo_code_id` int,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `order_item` (
  `order_id` int NOT NULL,
  `sku_id` int NOT NULL,
  `sku_code` varchar(100),
  `name` varchar(100) NOT NULL,
  `size` varchar(30),
  `color` varchar(30),
  `qty` int NOT NULL DEFAULT 1,
  `price` decimal(12,2) NOT NULL,
  `cost` decimal(12,2) NOT NULL,
  `discount_amount` decimal(12,2) NOT NULL,
  `shipping_fee` decimal(12,2) NOT NULL,
  `line_total` decimal(12,2) NOT NULL,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL,
  PRIMARY KEY (`order_id`, `sku_id`)
);

CREATE TABLE `payment` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `order_id` int UNIQUE NOT NULL,
  `method` varchar(30) NOT NULL,
  `status` varchar(30) NOT NULL,
  `paid_at` timestamp,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `shipment` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `order_id` int UNIQUE NOT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'pending',
  `shipped_at` timestamp,
  `delivered_at` timestamp,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `inquiry` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `customer_id` int NOT NULL,
  `status` varchar(30) NOT NULL,
  `customer_read_at` timestamp,
  `staff_read_at` timestamp,
  `closed_at` timestamp,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `message` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `inquiry_id` int NOT NULL,
  `sender_type` varchar(30) NOT NULL,
  `staff_id` int,
  `customer_id` int,
  `content` varchar(2000) NOT NULL,
  `sent_at` timestamp NOT NULL
);

CREATE TABLE `staff` (
  `id` integer PRIMARY KEY AUTO_INCREMENT,
  `password` varchar(255) NOT NULL,
  `email` varchar(100) UNIQUE NOT NULL,
  `name` varchar(30) NOT NULL,
  `phone` varchar(30),
  `role_id` int,
  `is_active` bool NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `role` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(30) UNIQUE NOT NULL,
  `member` bool NOT NULL DEFAULT 0,
  `orders` bool NOT NULL DEFAULT 0,
  `product` bool NOT NULL DEFAULT 0,
  `inquiry` bool NOT NULL DEFAULT 0,
  `statistic` bool NOT NULL DEFAULT 0,
  `staff` bool NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `category` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(30) UNIQUE NOT NULL,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `product` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `category_id` int NOT NULL,
  `name` varchar(100) NOT NULL,
  `description` varchar(2000),
  `is_active` bool NOT NULL DEFAULT 1,
  `is_deleted` bool NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `sku` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `product_id` int NOT NULL,
  `sku_code` varchar(100) UNIQUE NOT NULL,
  `size` varchar(30),
  `color` varchar(30),
  `price` decimal(12,2) NOT NULL,
  `cost` decimal(12,2) NOT NULL,
  `stock` int NOT NULL DEFAULT 0,
  `is_active` bool NOT NULL DEFAULT 1,
  `is_deleted` bool NOT NULL DEFAULT 0,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

CREATE TABLE `image` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `product_id` int NOT NULL,
  `url` varchar(500),
  `sort_order` int NOT NULL,
  `created_at` timestamp NOT NULL,
  `updated_at` timestamp NOT NULL
);

ALTER TABLE `wishlist` ADD FOREIGN KEY (`customer_id`) REFERENCES `customer` (`id`);

ALTER TABLE `cart` ADD FOREIGN KEY (`customer_id`) REFERENCES `customer` (`id`);

ALTER TABLE `orders` ADD FOREIGN KEY (`customer_id`) REFERENCES `customer` (`id`);

ALTER TABLE `orders` ADD FOREIGN KEY (`promo_code_id`) REFERENCES `promo_code` (`id`);

ALTER TABLE `payment` ADD FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`);

ALTER TABLE `shipment` ADD FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`);

ALTER TABLE `inquiry` ADD FOREIGN KEY (`customer_id`) REFERENCES `customer` (`id`);

ALTER TABLE `message` ADD FOREIGN KEY (`inquiry_id`) REFERENCES `inquiry` (`id`);

ALTER TABLE `message` ADD FOREIGN KEY (`customer_id`) REFERENCES `customer` (`id`);

ALTER TABLE `message` ADD FOREIGN KEY (`staff_id`) REFERENCES `staff` (`id`);

ALTER TABLE `staff` ADD FOREIGN KEY (`role_id`) REFERENCES `role` (`id`);

ALTER TABLE `product` ADD FOREIGN KEY (`category_id`) REFERENCES `category` (`id`);

ALTER TABLE `sku` ADD FOREIGN KEY (`product_id`) REFERENCES `product` (`id`);

ALTER TABLE `image` ADD FOREIGN KEY (`product_id`) REFERENCES `product` (`id`);

ALTER TABLE `wishlist_item` ADD FOREIGN KEY (`wishlist_id`) REFERENCES `wishlist` (`id`);

ALTER TABLE `wishlist_item` ADD FOREIGN KEY (`product_id`) REFERENCES `product` (`id`);

ALTER TABLE `cart_item` ADD FOREIGN KEY (`cart_id`) REFERENCES `cart` (`id`);

ALTER TABLE `cart_item` ADD FOREIGN KEY (`sku_id`) REFERENCES `sku` (`id`);

ALTER TABLE `order_item` ADD FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`);

ALTER TABLE `order_item` ADD FOREIGN KEY (`sku_id`) REFERENCES `sku` (`id`);

ALTER TABLE `promo_code_category` ADD FOREIGN KEY (`promo_code_id`) REFERENCES `promo_code` (`id`);

ALTER TABLE `promo_code_product` ADD FOREIGN KEY (`promo_code_id`) REFERENCES `promo_code` (`id`);

ALTER TABLE `promo_code_category` ADD FOREIGN KEY (`category_id`) REFERENCES `category` (`id`);

ALTER TABLE `promo_code_product` ADD FOREIGN KEY (`product_id`) REFERENCES `product` (`id`);
