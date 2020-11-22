USE master
GO
-- Create the new database if it does not exist already
IF NOT EXISTS (
       SELECT [name]
              FROM sys.databases
              WHERE [name] = N'RedisGearsTest'
)
CREATE DATABASE RedisGearsTest
GO

-- Create sample emp table
USE [RedisGearsTest]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[emp] (
    [empno] int NOT NULL,
    [fname] varchar(50),
    [lname] varchar(50),
    PRIMARY KEY ([empno])
)
GO
SELECT * FROM emp
GO
