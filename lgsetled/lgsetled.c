#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdlib.h>

#include <string.h>		/* for strerror(int errno) */
#include <errno.h>
extern int errno;

#define BUFS 1024
#define GET 0
#define SET 1
#define GET_MAX 2


int main(int argc, char **argv) {
	int op = -1;
	char *filename = NULL;
	int index;
	int c;

	opterr = 0;

	while ((c = getopt(argc, argv, "sgmf:")) != -1) {
		switch (c) {
		case 's':
			op = SET;
			break;
		case 'g':
			op = GET;
			break;
		case 'm':
			op = GET_MAX;
			break;
		case 'f':
			filename = optarg;
			break;
		case '?':
			if (optopt == 'f')
				fprintf(stderr, "Option -%c requires an argument.\n", optopt);
			else if (isprint(optopt))
				fprintf(stderr, "Unknown option `-%c'.\n", optopt);
			else
				fprintf(stderr, "Unknown option character `\\x%x'.\n", optopt);
			return 1;
		default:
			abort();
		}
	}

	if (op == -1) {
		fprintf(stderr, "Must supply either -s or -g to set or get a value.\n");
		return 1;
	}

	// Simple sanity check on the filename
	if (filename == NULL) {
		fprintf(stderr, "Argument -f <led_name> must be supplied.\n");
		return 1;
	}
	const char *invalid_characters = "./";
	char *cfilename = filename;
	while (*cfilename) {
		if (strchr(invalid_characters, *cfilename)) {
			fprintf(stderr, "Invalid character in device name\n");
			return 1;
		}
		cfilename++;
	}

	// Create the device paths
	char *device_path = "/sys/class/leds/";
	char *device_suffix = "/brightness";
	char *max_device_suffix = "/max_brightness";
	char *full_path = malloc(snprintf(NULL, 0, "%s%s%s", device_path, filename,
			device_suffix) + 1);
	sprintf(full_path, "%s%s%s", device_path, filename, device_suffix);
	char *full_max_path = malloc(snprintf(NULL, 0, "%s%s%s", device_path,
			filename, max_device_suffix) + 1);
	sprintf(full_max_path, "%s%s%s", device_path, filename, max_device_suffix);

	char str[50] = { 0 };

	if (op == GET) {
		// Get the LED brightness
		if (optind != argc) {
			fprintf(stderr, "Unknown argument`\\x%s'.\n", argv[optind]);
			return 1;
		}
		FILE *fp;
		int n;
		char buf[BUFS + 1];
		fprintf(stderr, "Opening: %s\n", full_path);
		if ((fp = fopen(full_path, "r")) == NULL) {
			fprintf(stderr, "Can't open brightness device file: %s\n",
					strerror(errno));
			return 1;
		}
		while (!feof(fp)) {
			if (fgets(str, 50, fp)) {
				printf("%s", str);
				break;
			}
		}
		fclose(fp);
		return 0;
	}

	// Get the max value, we need for both SET and GET_MAX
	FILE *max_fp;
	if ((max_fp = fopen(full_max_path, "r")) == NULL) {
		fprintf(stderr, "Can't open max_brightness device file: %s\n",
				strerror(errno));
		return 1;
	}
	int max_value = 0;
	while (!feof(max_fp)) {
		if (fgets(str, 50, max_fp)) {
			max_value = atoi(str);
			break;
		}
	}
	fclose(max_fp);

	if (op == GET_MAX) {
		printf("%d\n", max_value);
	} else {
		// Set the LED brightness
		if (optind != argc - 1) {
			fprintf(stderr, "Missing value argument\n");
			return 1;
		}

		// Sanity check the requested value
		int req_val = atoi(argv[optind]);
		if (req_val > max_value || req_val < 0) {
			fprintf(stderr,
					"Value out of range for this device %d (max %d).\n",
					req_val, max_value);
			return 1;
		}

		FILE *set_fp;
		if ((set_fp = fopen(full_path, "w")) == NULL) {
			fprintf(stderr,
					"Can't open brightness device file for writing: %s\n",
					strerror(errno));
			return 1;
		}
		fputs(argv[optind], set_fp);
		fclose(set_fp);
	}

	return 0;
}
