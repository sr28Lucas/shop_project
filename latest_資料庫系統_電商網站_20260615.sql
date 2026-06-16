CREATE TABLE `customer` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `password` varchar(255) NOT NULL,
  `email` varchar(100) UNIQUE NOT NULL,
  `name` varchar(30) NOT NULL,
  `phone` varchar(30),
  `region_id` int,
  `locality_id` int,
  `address` varchar(100),
  `is_active` bool NOT NULL DEFAULT 1,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `wishlist` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `customer_id` int UNIQUE NOT NULL,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `wishlist_item` (
  `wishlist_id` int NOT NULL,
  `product_id` int NOT NULL,
  `created_at` datetime,
  `updated_at` datetime,
  PRIMARY KEY (`wishlist_id`, `product_id`)
);

CREATE TABLE `cart` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `customer_id` int UNIQUE NOT NULL,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `cart_item` (
  `cart_id` int NOT NULL,
  `sku_id` int NOT NULL,
  `qty` int NOT NULL DEFAULT 1,
  `created_at` datetime,
  `updated_at` datetime,
  PRIMARY KEY (`cart_id`, `sku_id`)
);

CREATE TABLE `category` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(30) NOT NULL,
  `is_active` bool NOT NULL DEFAULT 1,
  `is_deleted` bool NOT NULL DEFAULT 0,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `product` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `category_id` int,
  `name` varchar(100) NOT NULL,
  `description` varchar(2000),
  `is_active` bool NOT NULL DEFAULT 1,
  `is_deleted` bool NOT NULL DEFAULT 0,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `variant` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `product_id` int NOT NULL,
  `color` varchar(30) NOT NULL,
  `is_active` bool NOT NULL DEFAULT 1,
  `is_deleted` bool NOT NULL DEFAULT 0,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `sku` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `variant_id` int NOT NULL,
  `sku_code` varchar(100) NOT NULL,
  `size` varchar(30),
  `price` decimal(12,2) NOT NULL,
  `cost` decimal(12,2) NOT NULL,
  `stock` int NOT NULL DEFAULT 0,
  `is_active` bool NOT NULL DEFAULT 1,
  `is_deleted` bool NOT NULL DEFAULT 0,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `image` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `product_id` int,
  `variant_id` int,
  `image_type` varchar(30) NOT NULL DEFAULT 'product',
  `filename` varchar(500) NOT NULL,
  `is_primary` bool NOT NULL DEFAULT 0,
  `sort_order` int NOT NULL DEFAULT 0,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `promo_code` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `code` varchar(30) NOT NULL,
  `description` varchar(100),
  `discount_type` varchar(30) NOT NULL,
  `discount_value` decimal(12,2) NOT NULL,
  `min_order_amount` decimal(12,2) NOT NULL DEFAULT 0,
  `usage_limit` int,
  `used_count` int NOT NULL DEFAULT 0,
  `is_active` bool NOT NULL DEFAULT 1,
  `is_deleted` bool NOT NULL DEFAULT 0,
  `start_at` datetime,
  `end_at` datetime,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `orders` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `customer_id` int NOT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'pending',
  `subtotal` decimal(12,2) NOT NULL,
  `shipping_fee` decimal(12,2) NOT NULL DEFAULT 0,
  `discount_total` decimal(12,2) NOT NULL DEFAULT 0,
  `total` decimal(12,2) NOT NULL,
  `promo_code_id` int,
  `promo_code_snapshot` varchar(30),
  `name` varchar(30) NOT NULL,
  `phone` varchar(30) NOT NULL,
  `region` varchar(30) NOT NULL,
  `locality` varchar(30) NOT NULL,
  `address` varchar(100) NOT NULL,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `order_item` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `product_id` int,
  `variant_id` int,
  `sku_id` int,
  `product_name` varchar(100) NOT NULL,
  `variant_name` varchar(100) NOT NULL,
  `sku_code` varchar(100) NOT NULL,
  `size` varchar(30),
  `color` varchar(30),
  `qty` int NOT NULL DEFAULT 1,
  `original_price` decimal(12,2) NOT NULL,
  `unit_price` decimal(12,2) NOT NULL,
  `unit_cost` decimal(12,2) NOT NULL
);

CREATE TABLE `payment` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `order_id` int UNIQUE NOT NULL,
  `method` varchar(30) NOT NULL,
  `card_number` varchar(30),
  `status` varchar(30) NOT NULL,
  `paid_at` datetime
);

CREATE TABLE `shipment` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `order_id` int UNIQUE NOT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'pending',
  `shipped_at` datetime,
  `delivered_at` datetime
);

CREATE TABLE `announcement` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `title` varchar(100) NOT NULL,
  `content` varchar(2000) NOT NULL,
  `type` varchar(30) NOT NULL,
  `target` varchar(30) NOT NULL DEFAULT 'all',
  `pin` bool NOT NULL DEFAULT 0,
  `is_active` bool NOT NULL DEFAULT 1,
  `is_deleted` bool NOT NULL DEFAULT 0,
  `start_at` datetime,
  `end_at` datetime,
  `created_at` datetime,
  `updated_at` datetime
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
  `announcement` bool NOT NULL DEFAULT 0,
  `return` bool NOT NULL DEFAULT 0,
  `promo` bool NOT NULL DEFAULT 0,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `staff` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `password` varchar(255) NOT NULL,
  `email` varchar(100) UNIQUE NOT NULL,
  `name` varchar(30) NOT NULL,
  `phone` varchar(30),
  `role_id` int NOT NULL,
  `is_active` bool NOT NULL DEFAULT 1,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `inquiry` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `customer_id` int NOT NULL,
  `purpose` varchar(100) NOT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'open',
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `message` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `inquiry_id` int NOT NULL,
  `staff_id` int,
  `customer_id` int,
  `content` varchar(2000) NOT NULL,
  `is_read` bool NOT NULL DEFAULT 0,
  `sent_at` datetime
);

CREATE TABLE `region` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `name` varchar(30) UNIQUE NOT NULL,
  `fee` decimal(12,2) NOT NULL DEFAULT 0,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `locality` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `region_id` int NOT NULL,
  `name` varchar(30)
);

CREATE TABLE `return_request` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `order_id` int NOT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'requested',
  `reason` varchar(2000),
  `requested_at` datetime,
  `approved_at` datetime,
  `rejected_at` datetime,
  `refunded_at` datetime,
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `return_item` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `return_request_id` int NOT NULL,
  `order_item_id` int NOT NULL,
  `qty` int NOT NULL,
  `reason` varchar(500),
  `status` varchar(30) NOT NULL DEFAULT 'requested',
  `created_at` datetime,
  `updated_at` datetime
);

CREATE TABLE `review` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `customer_id` int NOT NULL,
  `product_id` int NOT NULL,
  `order_item_id` int UNIQUE NOT NULL,
  `overall_rating` decimal(3,2) NOT NULL,
  `quality_rating` int NOT NULL,
  `comfort_rating` int NOT NULL,
  `value_rating` int NOT NULL,
  `fit_feedback` int NOT NULL,
  `comment` varchar(2000),
  `helpful_count` int NOT NULL DEFAULT 0,
  `created_at` datetime
);

ALTER TABLE `review` ADD FOREIGN KEY (`customer_id`) REFERENCES `customer` (`id`);

ALTER TABLE `review` ADD FOREIGN KEY (`product_id`) REFERENCES `product` (`id`);

ALTER TABLE `review` ADD FOREIGN KEY (`order_item_id`) REFERENCES `order_item` (`id`);

ALTER TABLE `wishlist` ADD FOREIGN KEY (`customer_id`) REFERENCES `customer` (`id`);

ALTER TABLE `wishlist_item` ADD FOREIGN KEY (`wishlist_id`) REFERENCES `wishlist` (`id`);

ALTER TABLE `wishlist_item` ADD FOREIGN KEY (`product_id`) REFERENCES `product` (`id`);

ALTER TABLE `cart` ADD FOREIGN KEY (`customer_id`) REFERENCES `customer` (`id`);

ALTER TABLE `cart_item` ADD FOREIGN KEY (`cart_id`) REFERENCES `cart` (`id`);

ALTER TABLE `cart_item` ADD FOREIGN KEY (`sku_id`) REFERENCES `sku` (`id`);

ALTER TABLE `product` ADD FOREIGN KEY (`category_id`) REFERENCES `category` (`id`);

ALTER TABLE `variant` ADD FOREIGN KEY (`product_id`) REFERENCES `product` (`id`);

ALTER TABLE `sku` ADD FOREIGN KEY (`variant_id`) REFERENCES `variant` (`id`);

ALTER TABLE `image` ADD FOREIGN KEY (`product_id`) REFERENCES `product` (`id`);

ALTER TABLE `image` ADD FOREIGN KEY (`variant_id`) REFERENCES `variant` (`id`);

ALTER TABLE `orders` ADD FOREIGN KEY (`customer_id`) REFERENCES `customer` (`id`);

ALTER TABLE `orders` ADD FOREIGN KEY (`promo_code_id`) REFERENCES `promo_code` (`id`);

ALTER TABLE `order_item` ADD FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`);

ALTER TABLE `payment` ADD FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`);

ALTER TABLE `shipment` ADD FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`);

ALTER TABLE `staff` ADD FOREIGN KEY (`role_id`) REFERENCES `role` (`id`);

ALTER TABLE `inquiry` ADD FOREIGN KEY (`customer_id`) REFERENCES `customer` (`id`);

ALTER TABLE `message` ADD FOREIGN KEY (`inquiry_id`) REFERENCES `inquiry` (`id`);

ALTER TABLE `message` ADD FOREIGN KEY (`staff_id`) REFERENCES `staff` (`id`);

ALTER TABLE `message` ADD FOREIGN KEY (`customer_id`) REFERENCES `customer` (`id`);

ALTER TABLE `customer` ADD FOREIGN KEY (`region_id`) REFERENCES `region` (`id`);

ALTER TABLE `customer` ADD FOREIGN KEY (`locality_id`) REFERENCES `locality` (`id`);

ALTER TABLE `locality` ADD FOREIGN KEY (`region_id`) REFERENCES `region` (`id`);

ALTER TABLE `return_request` ADD FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`);

ALTER TABLE `return_item` ADD FOREIGN KEY (`return_request_id`) REFERENCES `return_request` (`id`);

ALTER TABLE `return_item` ADD FOREIGN KEY (`order_item_id`) REFERENCES `order_item` (`id`);

ALTER TABLE customer ADD COLUMN is_verified TINYINT DEFAULT 0;
