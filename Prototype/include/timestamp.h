/**
 * @file timestamp.h
 * @author Jiahui Xie
 *
 * @section LICENSE
 *
 * Copyright © 2016 Jiahui Xie
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * @section DESCRIPTION
 *
 * Common header shared by both sender and receiver of a timestamp program.
 */

#ifndef TIMESTAMP_H
#define TIMESTAMP_H

#ifdef __cplusplus
extern "C" {
#endif

#include <getopt.h>
#include <unistd.h>

#ifdef __cplusplus
}
#endif

#define ENV_TIMESTAMP_OUTPUT "TIMESTAMP_OUTPUT"

enum class TimeStampMode : int {
        RECEIVE,
        SEND
};

struct timespec *timestamp_manipulate(struct timespec *ts, TimeStampMode mode);
#endif /* TIMESTAMP_H */
