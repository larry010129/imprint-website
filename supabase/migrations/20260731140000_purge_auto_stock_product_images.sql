-- Remove invented letter-SKU stock paths from product_images.
-- Admin product photos must be real uploads under /static/uploads/products/ only.
delete from product_images
where file_path ilike '%/shop-product/%'
   or file_path ilike '%\shop-product\%'
   or file_path ilike 'images/shop-product/%';
