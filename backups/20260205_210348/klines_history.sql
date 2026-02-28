--
-- PostgreSQL database dump
--

\restrict V5MOG4EVFIpIwBTKDRbe3K5Zy0NexhffNiHH9XVLh71GIcUUiD383ddwuxI99zm

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: klines_history; Type: TABLE DATA; Schema: public; Owner: dbuser
--

COPY public.klines_history (symbol, "interval", open_time, close_time, open_price, high_price, low_price, close_price, volume, quote_volume, number_of_trades, taker_buy_base_volume, taker_buy_quote_volume) FROM stdin;
\.


--
-- PostgreSQL database dump complete
--

\unrestrict V5MOG4EVFIpIwBTKDRbe3K5Zy0NexhffNiHH9XVLh71GIcUUiD383ddwuxI99zm

