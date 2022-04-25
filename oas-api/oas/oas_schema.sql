create table person
(
	person_id char(36) not null
		primary key,
	last_name varchar(64) null,
	first_name varchar(64) null,
	date_time_joined datetime default current_timestamp() not null,
	custodian_wallet_address char(42) not null,
	oauth_id varchar(100) not null,
	stx_secret varchar(200) null,
	stx_address varchar(50) ,
	constraint person_custodian_wallet_address_uindex
		unique (custodian_wallet_address)
);

create table artist
(
	artist_id char(36) not null
		primary key,
	date_time_started datetime default current_timestamp() not null,
	constraint artist_person_person_id_fk
		foreign key (artist_id) references person (person_id)
);

create table artwork
(
	artwork_id char(36) not null
		primary key,
	artist_id char(36) null,
	title varchar(256) null,
	medium varchar(256) not null,
	length decimal (5,2),
	width decimal (5,2),
	height decimal (5,2),
	description varchar(4096) null,
	short_description varchar(512) null,
	date_created date not null,
	nft_token_id char(64) null,
	nft_contract_address char(42) null,
	image_files_hash char(46) null,
	primary_image_file_name varchar(128) null,
	dimension_unit varchar(32) null,
	stx_contract_address varchar(100) null,
	stx_token_id varchar(42) null,
	constraint artwork_artist_artist_id_fk
		foreign key (artist_id) references artist (artist_id)
);

create table contact
(
	person_id char(36) not null,
	contact_id int not null,
	email varchar(64) null,
	phone_country_code int null,
	phone int null,
	primary key (person_id, contact_id),
	constraint contact_email_uindex
		unique (email),
	constraint contact_person_person_id_fk
		foreign key (person_id) references person (person_id)
);

create table non_fungible_token
(
	contract_address varchar(100) not null,
	token_id char(42) null,
	datetime_created datetime not null,
	artwork_id char(36) null,
	tx_hash varchar(66) not null,
	status varchar(32) null,
	blockchain varchar(20) null,
	primary key (contract_address, tx_hash),
	constraint nft_artwork_artwork_id_fk
		foreign key (artwork_id) references artwork (artwork_id)
);

create table ownership
(
	ownership_id int not null auto_increment,
	person_id char(36) not null,
	artwork_id char(36) not null,
	begin_date datetime not null,
	end_date datetime null,
	primary key (ownership_id, person_id, artwork_id),
	constraint ownership_artwork_artwork_id_fk
		foreign key (artwork_id) references artwork (artwork_id),
	constraint ownership_person_person_id_fk
		foreign key (person_id) references person (person_id)
);

create table listing
(
	person_id char(36) not null,
	artwork_id char(36) not null,
	ownership_id int not null,
	listing_id char(36) not null
		primary key,
	active tinyint(1) not null default '0',
	status int null default '0',
	constraint Listing_ownership_person_id_artwork_id_ownership_id_fk
		foreign key (ownership_id, person_id, artwork_id) references ownership (ownership_id, person_id, artwork_id)
);

create table listing_price
(
	price_id int not null auto_increment,
	listing_id char(36) not null,
	currency varchar(10) not null,
	amount decimal(20,6) null,
	tx_hash char(66) null,
	status tinyint(1) null default '0',
	primary key (price_id, listing_id),
	constraint listing_price_listing_listing_id_fk
		foreign key (listing_id) references listing (listing_id)
);

create table purchase
(
	purchase_id int not null auto_increment primary key,
	listing_id char(36) not null,
	buyer_id	char(36) not null,
	seller_id char(36) not null,
	status int null default '0',
	created_on datetime not null,
	completed_on datetime null,
	currency varchar(10) not null,
	tx_hash char(66) null,
	confirm_tx_hash char(66) null,
	constraint purchase_buyer_person_person_id_fk
		foreign key (buyer_id) references person (person_id),

	constraint purchase_seller_person_person_id_fk
		foreign key (buyer_id) references person (person_id),

	constraint purchase_listing_listing_id_fk
		foreign key (listing_id) references listing (listing_id)
);

create index ownership_person_person_id_index
	on ownership (person_id);

create table setting
(
	setting_id int auto_increment
		primary key,
	app_xpublic_key char(128) null
);

