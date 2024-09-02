from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, DoubleType, IntegerType

from config import configuration

def main():
    spark = SparkSession.builder.appName("SmartCityStreaming")\
    .config("spark.jars.packages",
            "org.apache.spark:spark-sql-kafka-0-10_2.13:3.5.0,"
            "org.apache.hadoop:hadoop-aws:3.3.1,"
            "com.amazonaws:aws-java-sdk:1.11.469,")\
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")\
    .config("spark.hadoop.fs.s3a.access.key", configuration.get('AWS_ACCESS_KEY'))\
    .config("spark.hadoop.fs.s3a.secret.key", configuration.get('AWS_SECRET_KEY'))\
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")\
    .getOrCreate()

    spark.sparkContext.setLogLevel('WARN')

    #vehicle schema
    vehicleSchema = StructType([
        StructField('id', StringType(), True),
        StructField('deviceId', StringType(), True),
        StructField('timestamp', TimestampType(), True),
        StructField('location', StringType(), True),
        StructField('speed', DoubleType(), True),
        StructField('direction', StringType(), True),
        StructField('make', StringType(), True),
        StructField('model', StringType(), True),
        StructField('year', IntegerType(), True),
        StructField('fuelType', StringType(), True),
    ])

    gpsSchema = StructType([
        StructField('id', StringType(), True),
        StructField('device_id', StringType(), True),
        StructField('timestamp', TimestampType(), True),
        StructField('speed', DoubleType(), True),
        StructField('direction', StringType(), True),
        StructField('vehicle_type', StringType(), True)
    ])

    trafficSchema = StructType([
        StructField('id', StringType(), True),
        StructField('device_id', StringType(), True),
        StructField('camera_id', StringType(), True),
        StructField('location', StringType(), True),
        StructField('timestamp', TimestampType(), True),
        StructField('snapshot', StringType(), True),

    ])

    weatherSchema = StructType([
        StructField('id', StringType(), True),
        StructField('device_id', StringType(), True),
        StructField('timestamp', TimestampType(), True),
        StructField('location', StringType(), True),
        StructField('temperature', DoubleType(), True),
        StructField('weatherCondition', StringType(), True),
        StructField('precipitation', DoubleType(), True),
        StructField('windSpeed', DoubleType(), True),
        StructField('humidity', IntegerType(), True),
        StructField('airQualityIndex', DoubleType(), True),

    ])

    emergencySchema = StructType([
        StructField('id', StringType(), True),
        StructField('device_id', StringType(), True),
        StructField('incident_id', StringType(), True),
        StructField('timestamp', TimestampType(), True),
        StructField('type', StringType(), True),
        StructField('location', StringType(), True),
        StructField('status', StringType(), True),
        StructField('description', StringType(), True),
    ])

    def read_kafka_topics(topic, schema):
        return (spark.readStream
                .format('kafka')
                .option('kafka.bootstrap.servers', 'broker:29092')
                .option('subscribe', topic)
                .option('startingOffsets', 'earliest')
                .load()
                .selectExpr('CAST(value AS STRING)')
                .select(from_json(col('value'), schema).alias('data'))
                .select('data.*')
                .withWatermark('timestamp', '2 minutes')
                )

    def streamWriter(input: DataFrame, checkpointFolder, output):
        return (input.writeStream
                .format('parquet')
                .option('checkpointLocation', checkpointFolder)
                .option('path', output)
                .outputMode('append')
                .start())

    vehicleDF = read_kafka_topics('vehicle_data', vehicleSchema).alias('vehicle')
    gpsDF = read_kafka_topics('gps_data', gpsSchema).alias('gps')
    trafficDF = read_kafka_topics('camera_data', trafficSchema).alias('camera')
    weatherDF = read_kafka_topics('weather_data', weatherSchema).alias('weather')
    emergencyDF = read_kafka_topics('emergency_data', emergencySchema).alias('emergency')

    query1 = streamWriter(vehicleDF, 's3a://smart-city-kabi/checkpoints/vehicle_data',
                          's3a://smart-city-kabi/data/vehicle_data')
    query2 = streamWriter(gpsDF, 's3a://smart-city-kabi/checkpoints/gps_data',
                          's3a://smart-city-kabi/data/gps_data')
    query3 = streamWriter(trafficDF, 's3a://smart-city-kabi/checkpoints/camera_data',
                          's3a://smart-city-kabi/data/camera_data')
    query4 = streamWriter(weatherDF, 's3a://smart-city-kabi/checkpoints/weather_data',
                          's3a://smart-city-kabi/data/weather_data')
    query5 = streamWriter(emergencyDF, 's3a://smart-city-kabi/checkpoints/emergency_data',
                          's3a://smart-city-kabi/data/emergency_data')

    query5.awaitTermination()


if __name__ == "__main__":
    main()